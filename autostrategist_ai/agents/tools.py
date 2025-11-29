"""Tools for querying the car sales and reparations databases using Spark SQL."""

import json

from databricks.connect import DatabricksSession
from databricks_langchain import ChatDatabricks
from langchain.agents import create_agent
from langchain.messages import HumanMessage
from langchain.tools import tool
from pyspark.dbutils import DBUtils

from autostrategist_ai.agents.data_structures import (
    MarketAnalysisResults,
    RepairAnalysisResults,
    RepairData,
    VehicleData,
)
from autostrategist_ai.agents.prompts import (
    MARKET_ANALYST_DESCRIPTION,
    MARKET_ANALYST_SYSTEM_PROMPT,
    REPAIR_SPECIALIST_DESCRIPTION,
    REPAIR_SPECIALIST_SYSTEM_PROMPT,
)

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
        clean_query += " LIMIT 100"

    print(f"DEBUG: Executing SQL -> {clean_query}")

    try:
        df = spark.sql(clean_query)
        results = [row.asDict() for row in df.collect()]

        # If the query worked but found NO results
        if not results:
            return json.dumps(
                {
                    "found": False,
                    "data": [],
                    "message": "Query returned 0 results. Try using broader wildcards (e.g. ILIKE "
                    "'%Mustang%') or removing filters like 'condition'.",
                }
            )

        # Check for aggregation queries that returned 0 count
        if len(results) == 1 and results[0].get("num_cars_sold", -1) == 0:
            return json.dumps(
                {
                    "found": False,
                    "data": results,
                    "message": "Aggregation found 0 matching cars. Relax filters: remove "
                    "condition, expand year range, or use broader model wildcard.",
                }
            )

        # Success - return the data
        return json.dumps({"found": True, "data": results, "row_count": len(results)})

    except Exception as e:
        # Return structured error so the LLM can self-correct
        return json.dumps(
            {
                "error": True,
                "message": f"SQL Execution Error: {str(e)}",
                "hint": "Check column names, table name, and SQL syntax. Use ILIKE not LIKE for"
                "case-insensitive matching.",
            }
        )


@tool
def execute_repair_sql(sql_query: str) -> str:
    """
    Executes a Spark SQL query against the reparations database.

    Args:
        sql_query: A valid Spark SQL query string.
                   ALWAYS use the full table name: workspace.car_sales.reparations
    """
    # Safety Guardrails
    forbidden_keywords = ["DROP", "DELETE", "ALTER", "TRUNCATE", "INSERT", "UPDATE"]
    if any(keyword in sql_query.upper() for keyword in forbidden_keywords):
        return json.dumps(
            {"error": True, "message": "Read-only access. Modification queries are not allowed."}
        )

    clean_query = sql_query.strip().rstrip(";")
    if "LIMIT" not in clean_query.upper():
        clean_query += " LIMIT 50"

    print(f"DEBUG: Executing Repair SQL -> {clean_query}")

    try:
        df = spark.sql(clean_query)
        results = [row.asDict() for row in df.collect()]

        if not results:
            return json.dumps(
                {
                    "found": False,
                    "data": [],
                    "message": "No repair records found. Try simpler component names (e.g.,"
                    "'brake' instead of 'brake pads').",
                }
            )

        return json.dumps({"found": True, "data": results, "row_count": len(results)})

    except Exception as e:
        return json.dumps(
            {
                "error": True,
                "message": f"SQL Execution Error: {str(e)}",
                "hint": "Use table workspace.car_sales.reparations. Check column names: component,"
                "diagnostic, cost.",
            }
        )


def build_market_query(vehicle_data: VehicleData) -> str:
    """
    Build a pre-formatted SQL query for market analysis.
    This reduces LLM errors by providing a template.
    """
    conditions = []

    if vehicle_data.manufacturer:
        conditions.append(f"manufacturer ILIKE '%{vehicle_data.manufacturer}%'")
    if vehicle_data.model:
        conditions.append(f"model ILIKE '%{vehicle_data.model}%'")
    if vehicle_data.year:
        # Use a 2-year range for better results
        conditions.append(f"year BETWEEN {vehicle_data.year - 1} AND {vehicle_data.year + 1}")
    if vehicle_data.condition:
        conditions.append(f"condition ILIKE '%{vehicle_data.condition}%'")

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    # Build query with odometer weighting if provided
    if vehicle_data.odometer:
        query = f"""
        SELECT 
            AVG(price) as average_price,
            PERCENTILE_APPROX(price, 0.5) as median_price,
            STDDEV(price) as price_std_dev,
            COUNT(*) as num_cars_sold
        FROM workspace.car_sales.vehicles_enriched
        WHERE {where_clause}
            AND odometer BETWEEN {vehicle_data.odometer - 20000} AND {vehicle_data.odometer + 20000}
            AND price > 0
        """
    else:
        query = f"""
        SELECT 
            AVG(price) as average_price,
            PERCENTILE_APPROX(price, 0.5) as median_price,
            STDDEV(price) as price_std_dev,
            COUNT(*) as num_cars_sold
        FROM workspace.car_sales.vehicles_enriched
        WHERE {where_clause}
            AND price > 0
        """

    return query.strip()


@tool("market_analyst", description=MARKET_ANALYST_DESCRIPTION)
def search_vehicle_database(vehicle_data: VehicleData) -> MarketAnalysisResults:
    """Search for price ranges for the given vehicle information.

    Args:
        vehicle_data (VehicleData): The vehicle data to search for.

    Returns:
        market_analysis_results (MarketAnalysisResults): The market analysis results
    """
    # First, try the pre-built query for reliability
    prebuilt_query = build_market_query(vehicle_data)
    print(f"DEBUG: Pre-built query -> {prebuilt_query}")

    result_str = execute_market_sql.invoke(prebuilt_query)
    result = json.loads(result_str)

    # If pre-built query succeeded, return directly
    if result.get("found") and result.get("data"):
        data = result["data"][0] if result["data"] else {}
        return {
            "average_price": data.get("average_price"),
            "median_price": data.get("median_price"),
            "price_std_dev": data.get("price_std_dev"),
            "num_cars_sold": data.get("num_cars_sold", 0),
        }

    # If pre-built query failed, fall back to LLM agent for flexibility
    print("DEBUG: Pre-built query returned no results, falling back to LLM agent")
    fallback_prompt = f"""
    Find market pricing for this vehicle: {vehicle_data.model_dump_json()}
    
    The initial query returned no results. Try these relaxation strategies:
    1. Remove condition filter
    2. Use broader year range (e.g., BETWEEN {(vehicle_data.year or 2015) - 3} AND 
        {(vehicle_data.year or 2015) + 3})
    3. Use simpler model matching (just the base model name)
    """

    user_input = {"messages": [HumanMessage(content=fallback_prompt)]}
    res_search = market_analyst_agent.invoke(user_input)

    try:
        results_dict = json.loads(res_search["messages"][-1].content)
        return results_dict
    except json.JSONDecodeError:
        return {
            "average_price": None,
            "median_price": None,
            "price_std_dev": None,
            "num_cars_sold": 0,
        }


def build_repair_query(repair_data: RepairData) -> str:
    """
    Build a pre-formatted SQL query for repair cost lookup.
    """
    conditions = []

    # Build OR conditions for each component
    if repair_data.components:
        component_conditions = []
        for comp in repair_data.components:
            comp_clean = comp.strip().lower()
            component_conditions.append(f"LOWER(component) LIKE '%{comp_clean}%'")
            component_conditions.append(f"LOWER(diagnostic) LIKE '%{comp_clean}%'")
        conditions.append(f"({' OR '.join(component_conditions)})")

    # Add diagnosis to search if provided
    if repair_data.diagnosis:
        diag_clean = repair_data.diagnosis.strip().lower()
        conditions.append(
            f"(LOWER(component) LIKE '%{diag_clean}%' OR LOWER(diagnostic) LIKE '%{diag_clean}%')"
        )

    where_clause = " OR ".join(conditions) if conditions else "1=1"

    query = f"""
    SELECT component, diagnostic, reparation_cost
    FROM workspace.car_sales.reparations
    WHERE {where_clause}
    """

    return query.strip()


@tool("repair_specialist", description=REPAIR_SPECIALIST_DESCRIPTION)
def search_reparation_database(repair_data: RepairData) -> RepairAnalysisResults:
    """Search for repair cost estimates based on components and diagnosis.

    Args:
        repair_data (RepairData): The repair data containing diagnosis and components.

    Returns:
        repair_analysis_results (RepairAnalysisResults): The analysis of the reparation costs
    """
    # First, try the pre-built query for reliability
    prebuilt_query = build_repair_query(repair_data)
    print(f"DEBUG: Pre-built repair query -> {prebuilt_query}")

    result_str = execute_repair_sql.invoke(prebuilt_query)
    result = json.loads(result_str)

    # If pre-built query succeeded, return directly
    if result.get("found") and result.get("data"):
        repairs = result["data"]
        total_cost = sum(r.get("reparation_cost", 0) for r in repairs if r.get("reparation_cost"))
        return {"identified_repairs": repairs, "total_estimated_cost": total_cost}

    # If pre-built query failed, fall back to LLM agent for flexibility
    print("DEBUG: Pre-built repair query returned no results, falling back to LLM agent")
    fallback_prompt = f"""
    Find repair costs for: {repair_data.model_dump_json()}
    
    The initial query returned no results. Try:
    1. Simpler component names (e.g., 'brake' instead of 'brake pads')
    2. Search diagnostic column for symptoms
    3. Use partial matching with LIKE '%keyword%'
    """

    user_input = {"messages": [HumanMessage(content=fallback_prompt)]}
    res_search = repair_specialist_agent.invoke(user_input)

    try:
        results_dict = json.loads(res_search["messages"][-1].content)
        return results_dict
    except json.JSONDecodeError:
        return {"identified_repairs": None, "total_estimated_cost": None}


market_analyst_agent = create_agent(
    model=llm, tools=[execute_market_sql], system_prompt=MARKET_ANALYST_SYSTEM_PROMPT
)

repair_specialist_agent = create_agent(
    model=llm, tools=[execute_repair_sql], system_prompt=REPAIR_SPECIALIST_SYSTEM_PROMPT
)
