import os

from databricks.connect import DatabricksSession
from pyspark.dbutils import DBUtils

spark = DatabricksSession.builder.getOrCreate()
dbutils = DBUtils(spark)

# Copy the CSV file to the Databricks Volume
csv_path = os.path.abspath(__file__ + "/reparation_data.csv")
dbutils.fs.cp(csv_path, "/Volumes/workspace/car_sales/raw_data/reparations.csv")
