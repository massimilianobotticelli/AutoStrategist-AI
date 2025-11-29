"""Workflow agent that integrates LLM with car sales and reparations databases."""

import dotenv
import mlflow
from databricks.connect import DatabricksSession
from databricks_langchain import ChatDatabricks
from langchain.agents import create_agent

from autostrategist_ai.agents.prompts import SYSTEM_PROMPT
from autostrategist_ai.agents.tools import search_reparation_database, search_vehicle_database
from autostrategist_ai.agents.config import (
    EXPERIMENT_PATH,
    LLM_ENDPOINT,
    TABLE_REPARATIONS,
    TABLE_VEHICLES,
)

dotenv.load_dotenv()

# Initialize Spark
spark = DatabricksSession.builder.getOrCreate()

# Set up MLflow experiment and autologging
mlflow.set_experiment(EXPERIMENT_PATH)
mlflow.langchain.autolog()


def get_table_schema_string(table_name: str) -> str:
    """
    Returns a string representation of the table schema
    (Column Name, Type) to feed into the LLM context.
    """
    try:
        # Get the schema from Spark
        schema = spark.table(table_name).schema

        # Format it nicely for the LLM
        schema_str = f"Table: {table_name}\nColumns:\n"
        for field in schema:
            schema_str += f"- {field.name} ({field.dataType.simpleString()})\n"

        return schema_str
    except Exception as e:
        return f"Error fetching schema for {table_name}: {e}"


llm = ChatDatabricks(endpoint=LLM_ENDPOINT)


market_table_context = get_table_schema_string(TABLE_VEHICLES)


# 1. Get Schema Context
repair_table_context = get_table_schema_string(TABLE_REPARATIONS)


# Create the Agent

graph = create_agent(
    model=llm,
    system_prompt=SYSTEM_PROMPT,
    tools=[search_vehicle_database, search_reparation_database],
)

mlflow.models.set_model(model=graph)
