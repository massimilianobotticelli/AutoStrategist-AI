"""
Ingestion Script

This script ingests vehicle and reparation data from CSV files located in a Databricks Volume
into Delta tables within the specified catalog and schema.
"""

import os

from databricks.connect import DatabricksSession

# Constants
CATALOG = "workspace"
SCHEMA = "car_sales"
VOLUME = "raw_data"
TARGET_VOLUME_PATH = f"/Volumes/{CATALOG}/{SCHEMA}/{VOLUME}/"

VEHICLE_CSV_NAME = "vehicles.csv"
REPAIR_CSV_NAME = "car_repair_costs.csv"

VEHICLE_TABLE = f"{CATALOG}.{SCHEMA}.vehicles"
REPAIR_TABLE = f"{CATALOG}.{SCHEMA}.reparations"


def ingest_csv_to_table(spark, csv_path, table_name):
    """
    Reads a CSV file and saves it as a Delta table if it doesn't exist.

    Args:
        spark: The Spark session.
        csv_path: Path to the CSV file.
        table_name: Target table name.
    """
    print(f"Reading data from {csv_path}...")
    try:
        df = spark.read.option("header", True).option("inferSchema", True).csv(csv_path)

        print(f"Writing data to {table_name} (mode=overwrite)...")
        df.write.format("delta").mode("overwrite").saveAsTable(table_name)
        print(f"Table {table_name} created successfully.")
    except Exception as e:
        print(f"Error ingesting {csv_path} to {table_name}: {e}")
        raise e


def main():
    """
    Main execution function for data ingestion.
    """
    # Initialize Spark
    spark = DatabricksSession.builder.getOrCreate()

    print(f"Starting ingestion process from volume: {TARGET_VOLUME_PATH}")

    # Ingest Vehicles
    vehicle_csv_path = os.path.join(TARGET_VOLUME_PATH, VEHICLE_CSV_NAME)
    ingest_csv_to_table(spark, vehicle_csv_path, VEHICLE_TABLE)

    # Ingest Reparations
    repair_csv_path = os.path.join(TARGET_VOLUME_PATH, REPAIR_CSV_NAME)
    ingest_csv_to_table(spark, repair_csv_path, REPAIR_TABLE)

    print("Ingestion process complete.")


if __name__ == "__main__":
    main()
