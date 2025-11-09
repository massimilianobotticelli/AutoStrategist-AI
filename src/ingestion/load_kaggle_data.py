import os
import shutil
from databricks.connect import DatabricksSession
from pyspark.dbutils import DBUtils

# --- 1. Initialize DatabricksSession (No local Java needed) ---
spark = DatabricksSession.builder.getOrCreate()
dbutils = DBUtils(spark)

# --- 2. Configure Env Vars BEFORE importing Kaggle ---
print("Configuring Kaggle credentials...")
try:
    # Try getting from Databricks Secrets
    # NOTE: When running locally, dbutils.secrets might fail if not specifically configured.
    # It's often easier to rely on local .env files for local dev,
    # but we'll keep this structure for when it runs as a deployed Job.
    os.environ['KAGGLE_USERNAME'] = dbutils.secrets.get(
        scope="hackathon_secrets", key="kaggle_username")
    os.environ['KAGGLE_KEY'] = dbutils.secrets.get(
        scope="hackathon_secrets", key="kaggle_key")
except Exception as e:
    print(f"Notice: Could not fetch secrets (expected during local debug if not fully configured). Checking local environment.")
    # Ensure you have these exported in your local terminal if debugging locally:
    # export KAGGLE_USERNAME=your_user
    # export KAGGLE_KEY=your_key
    if not os.environ.get('KAGGLE_USERNAME') or not os.environ.get('KAGGLE_KEY'):
        raise EnvironmentError(
            "KAGGLE_USERNAME and KAGGLE_KEY must be set via Databricks Secrets or local environment variables.")

# --- 3. LATE IMPORT (with isort skip) ---
from kaggle.api.kaggle_api_extended import KaggleApi  # isort: skip # noqa: E402

# --- 4. Execution ---
DATASET_NAME = "austinreese/craigslist-carstrucks-data"
# Fallbacks for local debugging if bundle vars aren't active
# CATALOG = spark.conf.get("bundle.catalog_name", "main")
# SCHEMA = spark.conf.get("bundle.schema_name", "car_sales")
# VOLUME = spark.conf.get("bundle.volume_name", "raw_data")
CATALOG = "workspace"
SCHEMA = "car_sales"
VOLUME = "raw_data"
TARGET_VOLUME_PATH = f"/Volumes/{CATALOG}/{SCHEMA}/{VOLUME}/"

print(f"Starting ingestion of {DATASET_NAME} to {TARGET_VOLUME_PATH}...")

api = KaggleApi()
api.authenticate()

# Use a temp path that works both locally and on Databricks cluster
local_path = "/tmp/kaggle_download"
if os.path.exists(local_path):
    shutil.rmtree(local_path)
os.makedirs(local_path)

print("Downloading from Kaggle...")
print(f"📥 Dataset: {DATASET_NAME}")
print(f"📁 Local download path: {local_path}")
api.dataset_download_files(DATASET_NAME, path=local_path, unzip=True)

# Show what was downloaded
print("📋 Download completed. Files found:")
for filename in os.listdir(local_path):
    file_path = os.path.join(local_path, filename)
    file_size = os.path.getsize(file_path)
    file_size_mb = file_size / (1024 * 1024)
    file_size_gb = file_size / (1024 * 1024 * 1024)

    if file_size_gb > 1:
        size_str = f"{file_size_gb:.2f} GB"
    else:
        size_str = f"{file_size_mb:.2f} MB"

    print(f"  📄 {filename}: {size_str}")

total_size = sum(os.path.getsize(os.path.join(local_path, f))
                 for f in os.listdir(local_path))
total_size_gb = total_size / (1024 * 1024 * 1024)
print(f"📊 Total download size: {total_size_gb:.2f} GB")

print(f"🏗️  Ensuring Volume exists at {CATALOG}.{SCHEMA}.{VOLUME}...")
print(f"📍 Target volume path: {TARGET_VOLUME_PATH}")

try:
    # These might fail if you don't have CREATE CATALOG permissions,
    # which is common in Free Edition. Best to create them once in the UI if this fails.
    print(f"🔧 Creating schema: {CATALOG}.{SCHEMA}")
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{SCHEMA}")

    print(f"🔧 Creating volume: {CATALOG}.{SCHEMA}.{VOLUME}")
    spark.sql(f"CREATE VOLUME IF NOT EXISTS {CATALOG}.{SCHEMA}.{VOLUME}")

    print("✅ Volume setup completed successfully!")

except Exception as e:
    print(f"⚠️  Warning: Auto-creation failed. Error: {e}")
    print("💡 You may need to create the catalog/schema/volume manually in the Databricks UI")

print(f"Moving files to Volume: {TARGET_VOLUME_PATH}")
for filename in os.listdir(local_path):
    # IMPORTANT: When running via Databricks Connect, standard python file operations
    # (like os.listdir) run LOCALLY on your laptop.
    # We need to move the file from LOCAL laptop -> REMOTE Volume.
    # dbutils.fs.cp with 'file:' prefix typically refers to the spark driver's local fs.
    # In DB Connect, this can be tricky.

    local_file_path = os.path.join(local_path, filename)
    target_file_path = os.path.join(TARGET_VOLUME_PATH, filename)

    # Get file size for progress tracking
    file_size = os.path.getsize(local_file_path)
    file_size_mb = file_size / (1024 * 1024)
    file_size_gb = file_size / (1024 * 1024 * 1024)

    if file_size_gb > 1:
        size_str = f"{file_size_gb:.2f} GB"
    else:
        size_str = f"{file_size_mb:.2f} MB"

    print(f"📁 File: {filename}")
    print(f"📏 Size: {size_str} ({file_size:,} bytes)")
    print(f"🚀 Starting upload to: {target_file_path}")
    print(f"⏰ Upload started at: {os.popen('date').read().strip()}")

    import time
    start_time = time.time()

    # For DB Connect file uploads, standard python copy to /Volumes often works
    # if the volume is mounted, BUT 'dbutils.fs.cp' is safer for remote execution.
    # Let's try the standard DB Connect compliant way:
    try:
        dbutils.fs.cp(f"file:{local_file_path}", target_file_path)

        end_time = time.time()
        duration = end_time - start_time
        duration_mins = duration / 60

        if duration > 60:
            time_str = f"{duration_mins:.1f} minutes"
        else:
            time_str = f"{duration:.1f} seconds"

        # Calculate upload speed
        upload_speed_mbps = (file_size_mb / duration) if duration > 0 else 0

        print(f"✅ Upload completed successfully!")
        print(f"⏱️  Duration: {time_str}")
        print(f"🚄 Average speed: {upload_speed_mbps:.2f} MB/s")
        print(f"📤 Uploaded at: {os.popen('date').read().strip()}")
        print("-" * 50)

    except Exception as e:
        end_time = time.time()
        duration = end_time - start_time
        print(f"❌ Upload failed after {duration:.1f} seconds")
        print(f"🚨 Error: {str(e)}")
        print("-" * 50)
        raise

# Cleanup local temp
shutil.rmtree(local_path)
print("Ingestion complete!")
