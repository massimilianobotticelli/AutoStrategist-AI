import json

from data_structures import MarketAnalysisResults, RepairAnalysisResults, RepairData, VehicleData
from databricks.connect import DatabricksSession
from databricks_langchain import ChatDatabricks
from langchain.agents import create_agent
from langchain.messages import HumanMessage
from langchain.tools import tool
from prompts import (
    market_analysit_description,
    market_analyst_system_prompt,
    repair_specialist_description,
    repair_specialist_system_prompt,
)
from pyspark.dbutils import DBUtils

# Initialize Spark and DBUtils
spark = DatabricksSession.builder.getOrCreate()
dbutils = DBUtils(spark)

llm = ChatDatabricks(endpoint="databricks-gpt-oss-120b")


@tool
def execute_market_sql(sql_query: str) -> str:
    """
    Executes a Spark SQL query against the car sales database.

    Args:
        sql_query: A valid Spark SQL query string.
                   ALWAYS use the full table name: workspace.car_sales.vehicles_enriched
    """
    # 1. Safety Guardrails (Basic)
    forbidden_keywords = ["DROP", "DELETE", "ALTER", "TRUNCATE", "INSERT", "UPDATE"]
    if any(keyword in sql_query.upper() for keyword in forbidden_keywords):
        return "Error: Read-only access. Modification queries are not allowed."

    clean_query = sql_query.strip().rstrip(";")
    if "LIMIT" not in clean_query.upper():
        clean_query += " LIMIT 20"

    print(f"DEBUG: Executing SQL -> {clean_query}")

    try:
        df = spark.sql(clean_query)
        results = [row.asDict() for row in df.collect()]

        # --- NEW LOGIC START ---
        # If the query worked but found NO cars (count=0 or empty list)
        if not results or results[0].get("num_cars_sold", 0) == 0:
            return json.dumps(
                {
                    "found": False,
                    "message": "Query returned 0 results. Try adding wildcards (e.g. ILIKE '%Mustang%') or removing the 'condition' filter.",
                }
            )
        # --- NEW LOGIC END ---

    except Exception as e:
        # Return the error so the LLM can self-correct!
        return f"SQL Execution Error: {str(e)}"


@tool("market_analyst", description=market_analysit_description)
def search_vehicle_database(vehicle_data: VehicleData) -> MarketAnalysisResults:
    """Search for price ranges for the given vehicle informtion.

    Args:
        vehicle_data (VehicleData): The vehicle data to search for.

    Returns:
        market_analysis_results (MarketAnalysisResults): The market analysis results
    """

    user_input = {"messages": [HumanMessage(content=vehicle_data.model_dump_json())]}
    res_search = market_analyst_agent.invoke(user_input)
    results_dict = json.loads(res_search["messages"][-1].content)
    market_analysis_results = results_dict  # MarketAnalysisResults(**results_dict)

    return market_analysis_results


@tool("repair_specialist", description=repair_specialist_description)
def search_reparation_database(repair_data: RepairData) -> RepairAnalysisResults:
    """Search for price ranges for the given vehicle informtion.

    Args:
        repair_data (RepairData): The vehicle data to search for.

    Returns:
        repair_analysis_results (RepairAnalysisResults): The analysis of the reparation costs
    """

    user_input = {"messages": [HumanMessage(content=repair_data.model_dump_json())]}
    res_search = repair_specialist_agent.invoke(user_input)
    results_dict = json.loads(res_search["messages"][-1].content)
    repair_analysis_results = results_dict  # RepairAnalysisResults(**results_dict)

    return repair_analysis_results


market_analyst_agent = create_agent(
    model=llm, tools=[execute_market_sql], system_prompt=market_analyst_system_prompt
)

repair_specialist_agent = create_agent(
    model=llm, tools=[execute_market_sql], system_prompt=repair_specialist_system_prompt
)
