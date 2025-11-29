"""Data Enrichment Script.

This script enriches vehicle data by extracting structured information from
unstructured text descriptions using a Large Language Model (LLM).

Workflow:
    1. Read vehicle data from the source Databricks table.
    2. Extract structured fields from free-text descriptions using LLM inference.
    3. Smart merge: Fill missing values in original columns with LLM-extracted data.
    4. Save the enriched dataset to the target Databricks table.

Key Features:
    - Uses Spark Pandas UDF for distributed LLM inference across partitions.
    - Initializes LLM client once per partition for efficiency.
    - Preserves original data when available, only filling null values.

Warning - LLM Implementation Notes:
    For production deployment, consider:
    * **Rate Limiting:** Implement backoff strategies for API rate limits.
    * **Caching:** Cache LLM responses to avoid redundant API calls.
    * **Validation:** Add schema validation for LLM-extracted data.
"""

import json
import os
from typing import Callable, Iterator

import pandas as pd
from config import EN_SOURCE_TABLE, EN_TARGET_TABLE, LLM_ENDPOINT
from databricks.connect import DatabricksSession
from databricks_langchain import ChatDatabricks
from langchain_core.prompts import PromptTemplate
from prompts import PROMPT_ENRICH_COLUMNS
from pyspark.dbutils import DBUtils
from pyspark.sql.functions import coalesce, col, pandas_udf
from pyspark.sql.types import StringType, StructField, StructType

# Schema for UDF output defining the structure of extracted vehicle information
SCHEMA: StructType = StructType(
    [
        StructField("manufacturer", StringType(), True),
        StructField("model", StringType(), True),
        StructField("year", StringType(), True),
        StructField("price", StringType(), True),
        StructField("odometer", StringType(), True),
        StructField("transmission", StringType(), True),
        StructField("fuel", StringType(), True),
        StructField("drive", StringType(), True),
        StructField("type", StringType(), True),
        StructField("paint_color", StringType(), True),
        StructField("condition", StringType(), True),
    ]
)


def get_credentials(dbutils: DBUtils) -> tuple[str, str]:
    """Retrieve Databricks credentials from environment or notebook context.

    Attempts to get credentials in the following order:
    1. Environment variables (DATABRICKS_HOST, DATABRICKS_TOKEN)
    2. Notebook context (when running in Databricks)

    Args:
        dbutils: Databricks utilities object for accessing notebook context.

    Returns:
        A tuple of (host_url, api_token) for Databricks authentication.

    Raises:
        ValueError: If credentials cannot be obtained from any source.

    Example:
        >>> db_host, db_token = get_credentials(dbutils)
        >>> print(f"Connecting to {db_host}")
    """
    db_host = os.environ.get("DATABRICKS_HOST")
    db_token = os.environ.get("DATABRICKS_TOKEN")

    if not db_host or not db_token:
        try:
            ctx = dbutils.notebook.entry_point.getDbutils().notebook().getContext()
            db_host = ctx.apiUrl().get()
            db_token = ctx.apiToken().get()
        except Exception:
            print("Warning: Could not fetch credentials from Notebook context.")

    if not db_host or not db_token:
        raise ValueError(
            "DATABRICKS_HOST and DATABRICKS_TOKEN must be set or available in context."
        )
    return db_host, db_token


def create_extract_vehicle_info_udf(
    service_host: str, service_token: str
) -> Callable[[Iterator[pd.Series]], Iterator[pd.DataFrame]]:
    """Create a Pandas UDF for extracting vehicle info from text descriptions.

    Factory function that creates a Spark Pandas UDF with captured credentials.
    The UDF uses an LLM to extract structured vehicle information from free-text
    descriptions.

    Args:
        service_host: Databricks workspace host URL for LLM endpoint access.
        service_token: Databricks API token for authentication.

    Returns:
        A Pandas UDF function that can be applied to a Spark DataFrame column.
        The UDF accepts text descriptions and returns a struct with extracted
        vehicle fields (manufacturer, model, year, price, etc.).

    Note:
        The returned UDF uses Iterator pattern for efficiency - the LLM client
        is initialized once per Spark partition rather than per row.
    """
    prompt = PromptTemplate(template=PROMPT_ENRICH_COLUMNS, input_variables=["free_text"])

    @pandas_udf(SCHEMA)
    def extract_vehicle_info_udf(
        iterator: Iterator[pd.Series],
    ) -> Iterator[pd.DataFrame]:
        """Process vehicle descriptions in batches using LLM inference.

        A Scalar Iterator Pandas UDF that extracts structured vehicle information
        from free-text descriptions. Uses Iterator pattern to initialize the LLM
        client once per Spark partition for efficiency.

        Args:
            iterator: Iterator of pandas Series, where each Series contains
                a batch of vehicle description strings from a Spark partition.

        Yields:
            pandas DataFrame with extracted vehicle fields for each batch.
            Each row contains: manufacturer, model, year, price, odometer,
            transmission, fuel, drive, type, paint_color, condition.

        Note:
            Failed extractions return empty dictionaries, resulting in null
            values for all fields in that row.
        """
        # --- WORKER INITIALIZATION (Runs once per partition) ---
        if service_host:
            os.environ["DATABRICKS_HOST"] = service_host
        if service_token:
            os.environ["DATABRICKS_TOKEN"] = service_token

        model = ChatDatabricks(endpoint=LLM_ENDPOINT)
        chain = prompt | model

        # --- BATCH PROCESSING ---
        for descriptions in iterator:
            results = []
            for text in descriptions:
                try:
                    response = chain.invoke({"free_text": text})

                    json_str = json.loads(response.content)[-1]["text"]

                    data = json.loads(json_str)
                    results.append(data)
                except Exception:
                    results.append({})

            yield pd.DataFrame(results)

    return extract_vehicle_info_udf


def main() -> None:
    """Execute the data enrichment pipeline.

    This is the main entry point that orchestrates the entire enrichment workflow:

    1. Initializes Spark session and retrieves Databricks credentials.
    2. Reads vehicle data from the configured source table.
    3. Creates and applies LLM-based UDF to extract info from descriptions.
    4. Smart merges extracted data with existing columns (fills nulls only).
    5. Saves enriched data to the target table.
    6. Reports statistics on recovered null values.

    Configuration:
        Source/target tables and LLM endpoint are configured via the `config`
        module: EN_SOURCE_TABLE, EN_TARGET_TABLE, LLM_ENDPOINT.

    Side Effects:
        - Writes enriched data to EN_TARGET_TABLE (overwrite mode).
        - Prints progress and statistics to stdout.

    Raises:
        ValueError: If Databricks credentials cannot be obtained.
        Exception: If data cannot be read, processed, or written.

    Note:
        Data is repartitioned to 8 partitions for parallelized LLM inference.
        Adjust based on cluster size and API rate limits.
    """
    # Initialize Spark and DBUtils
    spark = DatabricksSession.builder.getOrCreate()
    dbutils = DBUtils(spark)

    # Get Credentials
    db_host, db_token = get_credentials(dbutils)

    print(f"Reading data from {EN_SOURCE_TABLE}...")
    df_cleaned = spark.table(EN_SOURCE_TABLE)

    # Initial Stats
    initial_null_entries = df_cleaned.toPandas().isnull().sum().sum()
    print(f"Initial null entries: {initial_null_entries}")

    # Create UDF
    extract_vehicle_info_udf = create_extract_vehicle_info_udf(db_host, db_token)

    # Run Inference
    print("Running LLM inference to enrich data...")
    df_processed = df_cleaned.repartition(8).withColumn(
        "extracted_data", extract_vehicle_info_udf("description")
    )

    # Smart Merge Logic
    print("Merging extracted data with original columns...")
    extracted_schema_type = df_processed.schema["extracted_data"].dataType
    fillable_cols = extracted_schema_type.names
    final_columns = []

    for c in df_processed.columns:
        if c == "extracted_data":
            continue

        if c in fillable_cols:
            target_type = extracted_schema_type[c].dataType
            extracted_col = col("extracted_data")[c]
            original_casted = col(c).cast(target_type)
            extracted_casted = extracted_col.cast(target_type)
            merged_col = coalesce(original_casted, extracted_casted).alias(c)
            final_columns.append(merged_col)
        else:
            final_columns.append(col(c))

    df_final = df_processed.select(*final_columns).drop("description", "id")

    # Save Result
    print(f"Saving enriched data to {EN_TARGET_TABLE}...")
    df_final.write.mode("overwrite").saveAsTable(EN_TARGET_TABLE)

    # Final Stats
    df_final_read = spark.table(EN_TARGET_TABLE)
    final_null_entries = df_final_read.toPandas().isnull().sum().sum()
    recovered = initial_null_entries - final_null_entries
    percentage = round(recovered / initial_null_entries * 100, 2) if initial_null_entries > 0 else 0

    print(f"Final null entries: {final_null_entries}")
    print(f"Recovered entries: {recovered}")
    print(f"Percentage of recovered entries: {percentage}%")
    print("Enrichment process complete.")


if __name__ == "__main__":
    main()
