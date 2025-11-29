"""
Car Model Normalization Script.

This script normalizes car model names using an LLM (Large Language Model).
It reads cleaned vehicle data from a Databricks table, uses an LLM to identify
and standardize unique base model names from messy/inconsistent strings,
applies the normalization to the dataframe, and saves the cleaned result.

Workflow:
    1. Load vehicle data from the source Databricks table.
    2. Extract unique (manufacturer, model) pairs.
    3. Send pairs to LLM to identify canonical model names.
    4. Apply normalization rules to standardize model names.
    5. Save the cleaned data to the target Databricks table.

⚠️ LLM Implementation Notes & Optimizations:
    **Data normalization performed via LLM.** For production deployment,
    the following improvements are required:

    * **Robustness:** Expand the prompt with **few-shot examples** covering
      complex edge cases.
    * **Validation:** Implement automated tests to verify JSON schema compliance
      and output consistency.
    * **Caching:** Consider caching LLM responses to avoid redundant API calls
      for previously normalized models.
"""

from __future__ import annotations

import json

import mlflow
import pandas as pd
from config import CL_SOURCE_TABLE, CL_TARGET_TABLE, LLM_ENDPOINT
from databricks.connect import DatabricksSession
from databricks_langchain import ChatDatabricks
from langchain_core.prompts import PromptTemplate
from prompts import PROMPT_CLEAN_MODEL


def get_model_counts(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate and return counts of unique (manufacturer, model) pairs.

    Groups the dataframe by manufacturer and model, counts occurrences,
    and returns a sorted dataframe with only the manufacturer and model columns.

    Args:
        df: Input pandas DataFrame containing at least 'manufacturer' and 'model' columns.

    Returns:
        A pandas DataFrame with columns ['manufacturer', 'model'], sorted by
        manufacturer in descending order of count.

    Example:
        >>> df_counts = get_model_counts(df_vehicles)
        >>> print(df_counts.head())
           manufacturer     model
        0        toyota     camry
        1        toyota   corolla
        2          ford    f-150
    """
    df_models = (
        df.groupby(["manufacturer", "model"])
        .count()
        .sort_values(by=["manufacturer"], ascending=False)
        .reset_index()[["manufacturer", "model"]]
    )
    return df_models


def clean_model_names(
    df: pd.DataFrame, manufacturer_name: str, model_name: str
) -> pd.DataFrame:
    """
    Normalize model names in the dataframe for a specific manufacturer.

    Updates the 'model' column to the canonical model name where the manufacturer
    matches and the existing model string contains the base model name (case-insensitive).

    Args:
        df: Input pandas DataFrame containing 'manufacturer' and 'model' columns.
        manufacturer_name: The exact manufacturer name to filter on.
        model_name: The canonical/base model name to apply. Rows where the current
            model contains this string (case-insensitive) will be updated.

    Returns:
        The modified DataFrame with normalized model names. Note that the DataFrame
        is modified in place, but also returned for method chaining.

    Example:
        >>> df = clean_model_names(df, "toyota", "camry")
        # Rows like "Camry LE", "CAMRY XSE", "camry hybrid" become "camry"
    """
    # Identify rows to update
    mask = (df["manufacturer"] == manufacturer_name) & (
        df["model"].str.contains(model_name, case=False, na=False)
    )

    # Update in place using loc
    df.loc[mask, "model"] = model_name
    return df


def get_normalized_models_from_llm(
    unique_models_list: list[tuple[str, str]],
) -> dict[str, list[str]]:
    """
    Extract normalized base model names from raw model strings using an LLM.

    Sends a list of (manufacturer, model) tuples to a Large Language Model
    which identifies and returns canonical model names for each manufacturer.

    Args:
        unique_models_list: A list of tuples where each tuple contains
            (manufacturer_name, raw_model_string). For example:
            [("toyota", "Camry LE 2020"), ("toyota", "camry xse"), ("ford", "F-150 XLT")]

    Returns:
        A dictionary mapping manufacturer names to lists of canonical model names.
        For example: {"toyota": ["camry", "corolla"], "ford": ["f-150", "mustang"]}

    Raises:
        json.JSONDecodeError: If the LLM output cannot be parsed as valid JSON.
        KeyError: If the expected JSON structure is not present in the response.
        Exception: For any other errors during LLM invocation or parsing.

    Note:
        This function uses MLflow autologging for LangChain, so LLM calls
        are automatically tracked in the configured MLflow experiment.
    """

    prompt = PromptTemplate(template=PROMPT_CLEAN_MODEL, input_variables=["list_cars"])
    model = ChatDatabricks(endpoint=LLM_ENDPOINT)
    chain = prompt | model

    print("Invoking LLM for model normalization...")
    llm_input = {"list_cars": unique_models_list}
    llm_output = chain.invoke(llm_input)

    print("LLM invocation complete. Parsing output...")
    try:
        answer: str = json.loads(llm_output.content)[-1]["text"]
        dict_models: dict[str, list[str]] = json.loads(answer)
    except Exception as e:
        print(f"Error parsing LLM output: {e}")
        print(f"Raw output: {llm_output.content}")
        raise e

    return dict_models


def main() -> None:
    """
    Execute the car model normalization pipeline.

    This is the main entry point that orchestrates the entire workflow:

    1. Initializes Spark session and MLflow experiment tracking.
    2. Reads vehicle data from the configured source Databricks table.
    3. Converts to pandas DataFrame for in-memory processing.
    4. Extracts unique (manufacturer, model) pairs for LLM processing.
    5. Calls the LLM to get canonical model name mappings.
    6. Applies normalization to standardize all model names.
    7. Saves the cleaned DataFrame to the target Databricks table.

    Configuration:
        The source table, target table, and LLM endpoint are configured via
        the `config` module constants: CL_SOURCE_TABLE, CL_TARGET_TABLE, LLM_ENDPOINT.

    Raises:
        Exception: If LLM invocation fails or data cannot be read/written.

    Note:
        Assumes the dataset fits in driver memory for pandas conversion.
        For larger datasets, consider chunked processing or Spark UDFs.
    """
    # Initialize Spark and DBUtils
    spark = DatabricksSession.builder.getOrCreate()

    mlflow.set_experiment("/Shared/AutoStrategist-AI/")
    mlflow.langchain.autolog()

    print(f"Reading data from {CL_SOURCE_TABLE}...")
    sdf_vehicles = spark.table(CL_SOURCE_TABLE)

    # Convert to pandas (assuming small dataset fits in driver memory)
    print("Converting to Pandas DataFrame...")
    df_vehicles = sdf_vehicles.toPandas()

    print(f"Initial row count: {len(df_vehicles)}")

    # Prepare input for LLM
    unique_df = df_vehicles.drop_duplicates(subset=["manufacturer", "model"]).sort_values(
        by=["manufacturer", "model"]
    )
    grouped = unique_df.groupby(["manufacturer", "model"])
    unique_models_list = list(
        grouped.indices.keys()
    )  # keys of the groups are the (manufacturer, model) tuples

    # Get normalized models
    dict_models = get_normalized_models_from_llm(unique_models_list)

    print("Applying model normalization...")
    df_vehicles_cleaned = df_vehicles.copy()

    for mnf, models in dict_models.items():
        for m in models:
            # print(f"Normalizing {mnf}: {m}") # Optional: verbose logging
            df_vehicles_cleaned = clean_model_names(df_vehicles_cleaned, mnf, m)

    # Validation
    print("Normalization complete. Checking model counts...")
    print(get_model_counts(df_vehicles_cleaned).head())

    # Save result
    print(f"Saving cleaned data to {CL_TARGET_TABLE}...")
    spark.createDataFrame(df_vehicles_cleaned).write.mode("overwrite").saveAsTable(CL_TARGET_TABLE)
    print("Process complete.")


if __name__ == "__main__":
    main()
