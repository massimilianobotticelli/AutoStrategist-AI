"""
Data Preparation Script

This script reads raw vehicle data, filters for specific manufacturers,
cleans the data by removing unnecessary columns and invalid rows,
and saves the cleaned dataset to a new table.
"""

from databricks.connect import DatabricksSession
from pyspark.dbutils import DBUtils

# Constants
SOURCE_TABLE = "workspace.car_sales.vehicles"
TARGET_TABLE = "workspace.car_sales.vehicles_cleaned"
TARGET_MANUFACTURERS = ["ford", "toyota", "chevrolet", "honda"]
COLUMNS_TO_DROP = [
    "url",
    "region",
    "region_url",
    "VIN",
    "image_url",
    "county",
    "size",
    "title_status",
    "state",
    "lat",
    "long",
    "posting_date",
]
SAMPLE_FRACTION = 0.01


def main():
    """
    Main execution function for data preparation.
    """
    # Initialize Spark and DBUtils
    spark = DatabricksSession.builder.getOrCreate()
    # dbutils is initialized but not strictly used in this script,
    # keeping it if needed for future extensions or context.
    _ = DBUtils(spark)

    print(f"Reading data from {SOURCE_TABLE}...")
    df_original = spark.table(SOURCE_TABLE)

    # Filter by manufacturer and sample
    print(
        f"Filtering for manufacturers: {TARGET_MANUFACTURERS} and sampling {SAMPLE_FRACTION*100}%..."
    )
    df_filtered = df_original.filter(df_original.manufacturer.isin(TARGET_MANUFACTURERS)).sample(
        SAMPLE_FRACTION
    )

    # Drop unnecessary columns
    print(f"Dropping columns: {COLUMNS_TO_DROP}...")
    df_dropped = df_filtered.drop(*COLUMNS_TO_DROP)

    # Filter invalid rows
    print("Filtering invalid rows (price=0 or nulls in key columns)...")
    df_cleaned = df_dropped.filter(
        (df_dropped.price != 0)
        & df_dropped.year.isNotNull()
        & df_dropped.model.isNotNull()
        & df_dropped.odometer.isNotNull()
        & df_dropped.price.isNotNull()
    )

    # Log count
    row_count = df_cleaned.count()
    print(f"Cleaned dataset contains {row_count} rows.")

    # Write to table
    print(f"Writing cleaned data to {TARGET_TABLE}...")
    df_cleaned.write.mode("overwrite").saveAsTable(TARGET_TABLE)
    print("Data preparation complete.")


if __name__ == "__main__":
    main()
