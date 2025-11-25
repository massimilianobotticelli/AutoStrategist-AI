""" """

from databricks.connect import DatabricksSession
from pyspark.dbutils import DBUtils

# Initialize Spark and DBUtils
spark = DatabricksSession.builder.getOrCreate()
dbutils = DBUtils(spark)

df_original = spark.table("workspace.car_sales.vehicles")

df_cleaned = df_original.filter(
    df_original.manufacturer.isin("ford", "toyota", "chevrolet", "honda")
).sample(0.01)

df_cleaned = df_cleaned.drop(
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
)

df_cleaned = df_cleaned.filter(
    (df_cleaned.price != 0)
    & df_cleaned.year.isNotNull()
    & df_cleaned.model.isNotNull()
    & df_cleaned.odometer.isNotNull()
    & df_cleaned.price.isNotNull()
)

df_cleaned.count()

df_cleaned.write.mode("overwrite").saveAsTable("workspace.car_sales.vehicles_cleaned")
