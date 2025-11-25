""" """

import os

from databricks.connect import DatabricksSession
from pyspark.dbutils import DBUtils

# Initialize Spark and DBUtils
spark = DatabricksSession.builder.getOrCreate()
dbutils = DBUtils(spark)

df_cleaned = spark.table("workspace.car_sales.vehicles_models_cleaned")

pdf = df_cleaned.toPandas()
initial_null_entries = pdf.isnull().sum().sum()

import json
import os
from typing import Iterator

import pandas as pd

# LangChain / Databricks imports
from databricks_langchain import ChatDatabricks
from langchain_core.prompts import PromptTemplate

# PySpark imports
from pyspark.sql.functions import pandas_udf
from pyspark.sql.types import StringType, StructField, StructType

# ==============================================================================
# 1. CONFIGURATION & SCHEMA
# ==============================================================================

# Define the schema for the output JSON.
# Spark requires a strict schema for the UDF return type.
# We use StringType for most fields to avoid casting errors during extraction.
schema = StructType(
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

# ==============================================================================
# 2. CREDENTIAL CAPTURE (DRIVER SIDE)
# ==============================================================================

# We capture the notebook's authentication context here on the Driver.
# These variables will be "closed over" (pickled) and sent to the Worker nodes
# where the UDF actually runs.
ctx = dbutils.notebook.entry_point.getDbutils().notebook().getContext()
db_host = ctx.apiUrl().get()
db_token = ctx.apiToken().get()

# ==============================================================================
# 3. PROMPT DEFINITION
# ==============================================================================

prompt_template_content = """
You will get a free text. You need to extract the following information, if available:
- manufacturer
- model
- year
- price
- odometer in km
- transmission
- fuel
- drive (4wd, fwd, ...)
- type (SUV, hatchback, sedan)
- paint_color
- condition (like new, good, excellent, ...).

If some fields are not found in the text, return them as null.
Do not add any comment, answer only with a JSON format.

EXAMPLE:
free text: 2019 Ford Focus Sedan 2.0L 4dr Sedan 4WD 2019 Ford Focus Sedan 2.0L
answer:
{{
    "manufacturer": "ford",
    "model": "focus",
    "year": "2019",
    "price": null,
    "odometer": null,
    "transmission": null,
    "fuel": null,
    "drive": "4wd",
    "type": "sedan",
    "paint_color": null,
    "condition": null
}}

free text: {free_text}
"""

prompt = PromptTemplate(template=prompt_template_content, input_variables=["free_text"])

# ==============================================================================
# 4. ITERATOR UDF DEFINITION
# ==============================================================================


@pandas_udf(schema)
def extract_vehicle_info_udf(iterator: Iterator[pd.Series]) -> Iterator[pd.DataFrame]:
    """
    A Scalar Iterator UDF that processes data in batches (partitions).
    Using an Iterator allows us to initialize the LLM client ONCE per partition,
    rather than once per row, which significantly improves performance.
    """

    # --- WORKER INITIALIZATION (Runs once per partition) ---

    # Inject credentials into the Worker's environment variables.
    # The 'ChatDatabricks' client will look for these automatically.
    os.environ["DATABRICKS_HOST"] = db_host
    os.environ["DATABRICKS_TOKEN"] = db_token

    # Initialize the Model & Chain
    # We use a "Reasoning" model (e.g., 120b) or standard model.
    model = ChatDatabricks(endpoint="databricks-gpt-oss-120b")
    chain = prompt | model

    # --- BATCH PROCESSING ---
    for descriptions in iterator:
        results = []

        # Iterate through rows in the current batch
        for text in descriptions:
            try:
                # 1. Inference
                response = chain.invoke({"free_text": text})
                raw_content = response.content

                # 2. Robust Parsing Logic
                # Handles three cases:
                #   A. List Object (common in Reasoning models)
                #   B. Stringified List (string representation of A)
                #   C. Plain JSON String (standard models)

                final_json_str = "{}"

                # CASE A: The content is already a Python List
                if isinstance(raw_content, list):
                    text_block = next(
                        (item for item in raw_content if item.get("type") == "text"), None
                    )
                    if text_block:
                        final_json_str = text_block["text"]

                # CASE B & C: The content is a String
                elif isinstance(raw_content, str):
                    cleaned = raw_content.strip()

                    # Check for Stringified List (starts with [ and contains "type")
                    if cleaned.startswith("[") and "type" in cleaned:
                        try:
                            parsed_list = json.loads(cleaned)
                            text_block = next(
                                (item for item in parsed_list if item.get("type") == "text"), None
                            )
                            if text_block:
                                final_json_str = text_block["text"]
                        except:
                            pass  # Parsing failed, fall through to default
                    else:
                        # Assume it's a direct JSON string, strip markdown if present
                        final_json_str = cleaned.replace("```json", "").replace("```", "").strip()

                # 3. Final JSON Load
                # Ensure we have a valid JSON string before parsing
                if not final_json_str:
                    final_json_str = "{}"

                data = json.loads(final_json_str)
                results.append(data)

            except Exception:
                # Fail-safe: Return an empty dict to preserve row count.
                # This results in a row of nulls in Spark, which is safer than crashing.
                results.append({})

        # Yield the result batch as a Pandas DataFrame
        yield pd.DataFrame(results)


# RUN INFERENCE ---
df_processed = df_cleaned.repartition(8).withColumn(
    "extracted_data", extract_vehicle_info_udf("description")
)

from pyspark.sql.functions import coalesce, col

# ==============================================================================
# SMART MERGE / BACKFILL LOGIC
# ==============================================================================
# This script merges the original columns with the LLM-extracted data.
# Logic: Prioritize Original Data. If Original is Null, use Extracted Data.
#
# Solves two specific PySpark problems:
# 1. Type Mismatch: Handles merging an empty Double column (Original) with a String (LLM).
# 2. Keyword Conflicts: Handles columns named "size", "type", "year" without
#    confusing Spark's SQL parser.
# ==============================================================================

# 1. INSPECT SCHEMA
# We dynamically retrieve the schema from the 'extracted_data' struct column.
# This ensures we only try to merge fields that actually exist in the UDF output.
extracted_schema = df_processed.schema["extracted_data"].dataType

# 2. DEFINE TARGET COLUMNS
fillable_cols = extracted_schema.names

# 3. BUILD PROJECTION LIST
# We construct a list of column expressions to apply in a single .select() call.
# This is more efficient than looping with .withColumn().
final_columns = []

for c in df_processed.columns:
    # Skip the temporary 'extracted_data' struct itself (it will be dropped implicitly)
    if c == "extracted_data":
        continue

    if c in fillable_cols:
        # --- ROBUST MERGE LOGIC ----------------------------------------------

        # A. Identify Target Type
        #    Get the data type defined in the UDF schema (usually StringType).
        target_type = extracted_schema[c].dataType

        # B. Access Extracted Field Safely
        #    CRITICAL: We use bracket notation `col("struct")[name]` instead of
        #    dot notation `col("struct.name")`.
        #    This prevents Spark from confusing the column "size" with the
        #    built-in SQL function SIZE().
        extracted_col = col("extracted_data")[c]

        # C. Harmonize Types (Double Cast)
        #    If original 'size' is Double (because it was empty) and extracted
        #    'size' is String ("full-size"), a direct coalesce would fail.
        #    We cast the Original column to match the Extracted column's type.
        original_casted = col(c).cast(target_type)
        extracted_casted = extracted_col.cast(target_type)

        # D. Apply Coalesce
        #    coalesce(A, B) returns the first non-null value.
        #    Result: Original Value (if exists) OR Extracted Value (if Original was null).
        merged_col = coalesce(original_casted, extracted_casted).alias(c)

        final_columns.append(merged_col)

    else:
        # --- PASS-THROUGH LOGIC ----------------------------------------------
        # For columns like 'id', 'description', 'posting_date', just keep them as is.
        final_columns.append(col(c))

# 4. EXECUTE MERGE
# Apply the projection. This drops 'extracted_data' and updates the target columns.
df_final = df_processed.select(*final_columns)

df_final = df_final.drop("description", "id")

df_final.write.mode("overwrite").saveAsTable("workspace.car_sales.vehicles_enriched")

df_final_read = spark.table("workspace.car_sales.vehicles_enriched")

pdf = df_final_read.toPandas()
final_null_entries = pdf.isnull().sum().sum()

print(f"Number of null entries in the initial dataset: {initial_null_entries}")
print(f"Number of null entries in the final dataset: {final_null_entries}")
print(f"Recovered entries: {initial_null_entries - final_null_entries}")
print(
    f"Percentage of recovered entries: {round((initial_null_entries - final_null_entries) / initial_null_entries * 100, 2)}%"
)
