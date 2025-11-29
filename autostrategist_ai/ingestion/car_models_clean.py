"""
Car Model Normalization Script

This script normalizes car model names using an LLM.
It reads cleaned vehicle data, uses a Large Language Model to identify unique base model names
from messy strings, cleans the dataframe, and saves the result.

⚠️ LLM Implementation Notes & Optimizations
**Data normalization performed via LLM.** For production deployment, the following improvements are
    required:
* **Robustness:** Expand the prompt with **few-shot examples** covering complex edge cases.
* **Validation:** Implement automated tests to verify JSON schema compliance and output consistency.
"""

import json

import mlflow
from databricks.connect import DatabricksSession
from databricks_langchain import ChatDatabricks
from langchain_core.prompts import PromptTemplate
from prompts import PROMPT_CLEAN_MODEL

# Constants
SOURCE_TABLE = "workspace.car_sales.vehicles_cleaned"
TARGET_TABLE = "workspace.car_sales.vehicles_models_cleaned"
LLM_ENDPOINT = "databricks-gpt-oss-120b"


def get_model_counts(df):
    """
    Returns a dataframe with counts of (manufacturer, model) pairs.
    """
    df_models = (
        df.groupby(["manufacturer", "model"])
        .count()
        .sort_values(by=["manufacturer"], ascending=False)
        .reset_index()[["manufacturer", "model"]]
    )
    return df_models


def clean_model_names(df, manufacturer_name, model_name):
    """
    Updates the 'model' column in the dataframe where the manufacturer matches
    and the model string contains the base model name.
    """
    # Identify rows to update
    mask = (df["manufacturer"] == manufacturer_name) & (
        df["model"].str.contains(model_name, case=False, na=False)
    )

    # Update in place using loc
    df.loc[mask, "model"] = model_name
    return df


def get_normalized_models_from_llm(unique_models_list):
    """
    Invokes the LLM to extract unique base model names from a list of (manufacturer, model) tuples.
    """

    prompt = PromptTemplate(template=PROMPT_CLEAN_MODEL, input_variables=["list_cars"])
    model = ChatDatabricks(endpoint=LLM_ENDPOINT)
    chain = prompt | model

    print("Invoking LLM for model normalization...")
    llm_input = {"list_cars": unique_models_list}
    llm_output = chain.invoke(llm_input)

    print("LLM invocation complete. Parsing output...")
    try:
        answer = json.loads(llm_output.content)[-1]["text"]
        dict_models = json.loads(answer)
    except Exception as e:
        print(f"Error parsing LLM output: {e}")
        print(f"Raw output: {llm_output.content}")
        raise e

    return dict_models


def main():
    """
    Main execution function.
    """
    # Initialize Spark and DBUtils
    spark = DatabricksSession.builder.getOrCreate()

    mlflow.set_experiment("/Shared/AutoStrategist-AI/")
    mlflow.langchain.autolog()

    print(f"Reading data from {SOURCE_TABLE}...")
    sdf_vehicles = spark.table(SOURCE_TABLE)

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
    print(f"Saving cleaned data to {TARGET_TABLE}...")
    spark.createDataFrame(df_vehicles_cleaned).write.mode("overwrite").saveAsTable(TARGET_TABLE)
    print("Process complete.")


if __name__ == "__main__":
    main()
