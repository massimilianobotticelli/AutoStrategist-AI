"""
### ⚠️ LLM Implementation Notes & Optimizations

**Data normalization performed via LLM.** For production deployment, the following improvements are required:
* **Robustness:** Expand the prompt with **few-shot examples** covering complex edge cases (e.g., distinguishing trims vs. models).
* **Validation:** Implement automated tests to verify JSON schema compliance and output consistency.
"""

from databricks.connect import DatabricksSession
from pyspark.dbutils import DBUtils
import json

import mlflow
import pandas as pd
from databricks_langchain import ChatDatabricks
from langchain_core.prompts import PromptTemplate

# Initialize Spark and DBUtils
spark = DatabricksSession.builder.getOrCreate()
dbutils = DBUtils(spark)

mlflow.langchain.autolog()

sdf_vehicles = spark.table("workspace.car_sales.vehicles_cleaned")

sdf_vehicles.printSchema()
sdf_vehicles.count()

# Convert to pandas due to the small dataset
df_vehicles = sdf_vehicles.toPandas()

df_vehicles.groupby("manufacturer").count()


def check_model_names(df):
    df_models = (
        df.groupby(["manufacturer", "model"])
        .count()
        .sort_values(by=["manufacturer"], ascending=False)
        .reset_index()[["manufacturer", "model"]]
    )
    return df_models


def clean_model_names(df, manufacturer_name, model_name):
    df_updated = df.copy()
    df_model_specific = df_updated[
        (df_updated["manufacturer"] == manufacturer_name)
        & (df_updated["model"].str.contains(model_name))
    ]
    df_updated.iloc[df_model_specific.index, df_updated.columns.get_loc("model")] = model_name
    return df_updated


check_model_names(df_vehicles)

prompt_template_content = """
You are a car expert. You are given a list of car models with extraneous details included in the model string (like engine volume, door count, body type, etc.). Your task is to extract and return a list of the **unique, base model names** from this input.

Important: return only the json without any comments!

Example:

Input:
[
    ("toyota", "corolla 4dr 2.0l 4cyl 2wd"),
    ("toyota", "yaris 4dr 4cyl"),
    ("toyota", "yaris 1.5l 2wd"),
    ("chevrolet", "silverado 1500 extended cab")
]

Output:
{{ 
    "toyota": ["corolla", "yaris"],
    "chevrolet": ["silverado"]
}}

list of cars: {list_cars}
"""

prompt = PromptTemplate(template=prompt_template_content, input_variables=["list_cars"])

model = ChatDatabricks(endpoint="databricks-gpt-oss-120b")
chain = prompt | model

unique_df = df_vehicles.drop_duplicates().sort_values(by=["manufacturer", "model"])
grouped = unique_df.groupby(["manufacturer", "model"])

llm_input = {"list_cars": list(grouped.indices)}
llm_output = chain.invoke(llm_input)
answer = json.loads(llm_output.content)[-1]["text"]
dict_models = json.loads(answer)

df_vehicles_cleaned = df_vehicles.copy()

for mnf, models in dict_models.items():
    for m in models:
        print(mnf, m)
        df_vehicles_cleaned = clean_model_names(df_vehicles_cleaned, mnf, m)

check_model_names(df_vehicles_cleaned)

spark.createDataFrame(df_vehicles_cleaned).write.mode("overwrite").saveAsTable(
    "workspace.car_sales.vehicles_models_cleaned"
)
