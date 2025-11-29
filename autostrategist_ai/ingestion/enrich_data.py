"""
Data Enrichment Script

This script enriches vehicle data by extracting structured information from unstructured text descriptions
using a Large Language Model (LLM). It handles data reading, LLM inference via a Spark UDF,
smart merging of extracted data with existing columns, and saving the enriched dataset.
"""

import json
import os
from typing import Iterator

import pandas as pd
from config import EN_SOURCE_TABLE, EN_TARGET_TABLE, LLM_ENDPOINT
from databricks.connect import DatabricksSession
from databricks_langchain import ChatDatabricks
from langchain_core.prompts import PromptTemplate
from prompts import PROMPT_ENRICH_COLUMNS
from pyspark.dbutils import DBUtils
from pyspark.sql.functions import coalesce, col, pandas_udf
from pyspark.sql.types import StringType, StructField, StructType

# Schema for UDF Output
SCHEMA = StructType(
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


def get_credentials(dbutils):
    """
    Retrieves Databricks credentials from environment variables or notebook context.
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


def create_extract_vehicle_info_udf(service_host, service_token):
    """
    Factory function to create the UDF with captured credentials.
    """
    prompt = PromptTemplate(template=PROMPT_ENRICH_COLUMNS, input_variables=["free_text"])

    @pandas_udf(SCHEMA)
    def extract_vehicle_info_udf(iterator: Iterator[pd.Series]) -> Iterator[pd.DataFrame]:
        """
        A Scalar Iterator UDF that processes data in batches (partitions).
        Using an Iterator allows us to initialize the LLM client ONCE per partition.
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


def main():
    """
    Main execution function.
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
