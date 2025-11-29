"""Data Ingestion Script.

This script ingests vehicle and reparation data from CSV files located in a
Databricks Volume into Delta tables within the specified catalog and schema.

Workflow:
    1. Connect to Databricks using the configured Spark session.
    2. Read vehicle data CSV from the Unity Catalog Volume.
    3. Write vehicle data to a Delta table (overwrite mode).
    4. Read reparation data CSV from the Unity Catalog Volume.
    5. Write reparation data to a Delta table (overwrite mode).

Configuration:
    All paths and table names are configured via the `config` module:
    - CATALOG, SCHEMA, VOLUME: Unity Catalog location
    - VEHICLE_CSV_NAME, VEHICLE_TABLE: Vehicle data source and target
    - REPAIR_CSV_NAME, REPAIR_TABLE: Reparation data source and target
"""

import os

from config import (
    CATALOG,
    REPAIR_CSV_NAME,
    REPAIR_TABLE,
    SCHEMA,
    VEHICLE_CSV_NAME,
    VEHICLE_TABLE,
    VOLUME,
)
from databricks.connect import DatabricksSession
from pyspark.sql import SparkSession

# Path to the Unity Catalog Volume containing source CSV files
TARGET_VOLUME_PATH: str = f"/Volumes/{CATALOG}/{SCHEMA}/{VOLUME}/"


def ingest_csv_to_table(spark: SparkSession, csv_path: str, table_name: str) -> None:
    """Read a CSV file and save it as a Delta table.

    Reads data from the specified CSV file path, infers the schema, and writes
    it to a Delta table in overwrite mode. The table is created if it doesn't
    exist, or completely replaced if it does.

    Args:
        spark: Active Spark session for reading and writing data.
        csv_path: Absolute path to the source CSV file in the Databricks
            Volume (e.g., '/Volumes/catalog/schema/volume/file.csv').
        table_name: Fully qualified Delta table name to write to
            (e.g., 'catalog.schema.table_name').

    Raises:
        Exception: If the CSV file cannot be read or the table cannot be written.
            Common causes include invalid paths, permission issues, or schema
            inference failures.

    Example:
        >>> ingest_csv_to_table(spark, '/Volumes/main/default/data/cars.csv',
        ...                     'main.default.vehicles')
        Reading data from /Volumes/main/default/data/cars.csv...
        Writing data to main.default.vehicles (mode=overwrite)...
        Table main.default.vehicles created successfully.
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


def main() -> None:
    """Execute the data ingestion pipeline.

    This is the main entry point that orchestrates the ingestion of both
    vehicle and reparation datasets:

    1. Initializes a Databricks Spark session.
    2. Ingests vehicle data from CSV to Delta table.
    3. Ingests reparation data from CSV to Delta table.

    The source CSV files are read from the configured Unity Catalog Volume,
    and the data is written to Delta tables in overwrite mode.

    Side Effects:
        - Creates or overwrites VEHICLE_TABLE with vehicle data.
        - Creates or overwrites REPAIR_TABLE with reparation data.
        - Prints progress messages to stdout.

    Raises:
        Exception: If any CSV file cannot be read or any table cannot be written.
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
