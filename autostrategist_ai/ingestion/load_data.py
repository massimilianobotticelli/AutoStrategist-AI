"""
Ingestion script to download Kaggle dataset to Databricks Volume.
"""

import os

from config import CATALOG, DATASET_NAME, SCHEMA, VOLUME
from databricks.connect import DatabricksSession
from pyspark.dbutils import DBUtils
from reparation_data import REPARATION_CSV

# Initialize Spark and DBUtils
spark = DatabricksSession.builder.getOrCreate()
dbutils = DBUtils(spark)

# Setup volume configuration
TARGET_VOLUME_PATH = f"/Volumes/{CATALOG}/{SCHEMA}/{VOLUME}/"


# Kaggle credentials setup
print("Configuring Kaggle credentials...")
try:
    # Try to fetch secrets from Databricks
    os.environ["KAGGLE_USERNAME"] = dbutils.secrets.get(
        scope="hackathon_secrets", key="kaggle_username"
    )
    os.environ["KAGGLE_KEY"] = dbutils.secrets.get(scope="hackathon_secrets", key="kaggle_key")
    from kaggle.api.kaggle_api_extended import KaggleApi  # isort: skip # noqa: E402
except (KeyError, AttributeError, RuntimeError) as e:
    print("Notice: Could not fetch secrets. Checking local environment.")
    raise e

if not os.environ.get("KAGGLE_USERNAME") or not os.environ.get("KAGGLE_KEY"):
    raise EnvironmentError(
        "KAGGLE_USERNAME and KAGGLE_KEY must be set via Databricks Secrets or local"
        " environment variables."
    )


def create_volume_if_not_exists():
    """
    Creates the specified catalog, schema, and volume if they do not exist.
    """
    try:
        print(f"🔧 Creating schema: {CATALOG}.{SCHEMA}")
        spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{SCHEMA}")
        print(f"🔧 Creating volume: {CATALOG}.{SCHEMA}.{VOLUME}")
        spark.sql(f"CREATE VOLUME IF NOT EXISTS {CATALOG}.{SCHEMA}.{VOLUME}")
        print("✅ Volume setup completed successfully!")
    except Exception as e:
        print(f"⚠️  Warning: Auto-creation failed. Error: {e}")
        print("💡 You may need to create the catalog/schema/volume manually in the Databricks UI")
        raise e


def download_from_kaggle():
    """
    Downloads the specified dataset from Kaggle into the target volume path.
    """
    print(f"Starting ingestion of {DATASET_NAME} to {TARGET_VOLUME_PATH}...")

    api = KaggleApi()
    api.authenticate()

    print("Downloading from Kaggle...")
    print(f"📥 Dataset: {DATASET_NAME}")
    print(f"📁 Local download path: {TARGET_VOLUME_PATH}")

    api.dataset_download_files(DATASET_NAME, path=TARGET_VOLUME_PATH, unzip=True)

    print("📋 Download completed. Files found:")
    if os.path.exists(TARGET_VOLUME_PATH):
        total_size = 0
        for filename in os.listdir(TARGET_VOLUME_PATH):
            file_path = os.path.join(TARGET_VOLUME_PATH, filename)
            file_size = os.path.getsize(file_path)
            total_size += file_size

            file_size_mb = file_size / (1024 * 1024)
            file_size_gb = file_size / (1024 * 1024 * 1024)
            size_str = f"{file_size_gb:.2f} GB" if file_size_gb > 1 else f"{file_size_mb:.2f} MB"
            print(f"  📄 {filename}: {size_str}")

        total_size_gb = total_size / (1024 * 1024 * 1024)
        print(f"📊 Total download size: {total_size_gb:.2f} GB")

    print(f"🏗️  Ensuring Volume exists at {CATALOG}.{SCHEMA}.{VOLUME}...")
    print(f"📍 Target volume path: {TARGET_VOLUME_PATH}")
    print("Ingestion complete!")


def load_reparation_data():
    """Loads reparation data into a Delta table."""
    csv_path = os.path.join(TARGET_VOLUME_PATH, "car_repair_costs.csv")
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write(REPARATION_CSV.strip())
    print(f"CSV written to {csv_path}")


def main():
    """Main execution flow."""
    create_volume_if_not_exists()
    download_from_kaggle()
    load_reparation_data()


if __name__ == "__main__":
    main()
