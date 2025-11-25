"""
Ingest vehicle and reparation data from CSV files into Databricks tables.
"""

import os

from databricks.connect import DatabricksSession
from pyspark.dbutils import DBUtils

# Initialize Spark and DBUtils
spark = DatabricksSession.builder.getOrCreate()
dbutils = DBUtils(spark)

# Setup volume configuration
CATALOG = "workspace"
SCHEMA = "car_sales"
VOLUME = "raw_data"
TARGET_VOLUME_PATH = f"/Volumes/{CATALOG}/{SCHEMA}/{VOLUME}/"

# Define the path to the CSV file
vehicle_csv_path = os.path.join(TARGET_VOLUME_PATH, "vehicles.csv")

# Read the CSV file into a Spark DataFrame
vehicles_df = spark.read.option("header", True).option("inferSchema", True).csv(vehicle_csv_path)

# Save the DataFrame as a table in the workspace.car_sales schema, only if it does not exist
vehicles_df.write.format("delta").mode("ignore").saveAsTable("workspace.car_sales.vehicles")

print("Table workspace.car_sales.vehicles created if it did not exist.")

# Define the path to the CSV file
repair_csv_path = os.path.join(TARGET_VOLUME_PATH, "car_repair_costs.csv")

# Read the CSV file into a Spark DataFrame
repair_df = spark.read.option("header", True).option("inferSchema", True).csv(repair_csv_path)

# Save the DataFrame as a table in the workspace.car_sales schema, only if it does not exist
repair_df.write.format("delta").mode("ignore").saveAsTable("workspace.car_sales.reparations")

print("Table workspace.car_sales.reparations created if it did not exist.")
