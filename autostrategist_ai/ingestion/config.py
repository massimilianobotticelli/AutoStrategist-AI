"""Configuration constants for data ingestion."""

LLM_ENDPOINT = "databricks-gpt-oss-120b"

# Load data constants
CATALOG = "workspace"
SCHEMA = "car_sales"
VOLUME = "raw_data"
DATASET_NAME = "austinreese/craigslist-carstrucks-data"

# Ingestion data constants
VEHICLE_TABLE = f"{CATALOG}.{SCHEMA}.vehicles"
REPAIR_TABLE = f"{CATALOG}.{SCHEMA}.reparations"
VEHICLE_CSV_NAME = "vehicles.csv"
REPAIR_CSV_NAME = "car_repair_costs.csv"


# Prepare data constants
PREP_SOURCE_TABLE = f"{CATALOG}.{SCHEMA}.vehicles"
PREP_TARGET_TABLE = f"{CATALOG}.{SCHEMA}.vehicles_cleaned"
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

# Car models cleaning constants
CL_SOURCE_TABLE = f"{CATALOG}.{SCHEMA}.vehicles_cleaned"
CL_TARGET_TABLE = f"{CATALOG}.{SCHEMA}.vehicles_models_cleaned"

# Enrich data constants
EN_SOURCE_TABLE = f"{CATALOG}.{SCHEMA}.vehicles_models_cleaned"
EN_TARGET_TABLE = f"{CATALOG}.{SCHEMA}.vehicles_enriched"
