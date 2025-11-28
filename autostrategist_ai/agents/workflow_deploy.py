import dotenv
import mlflow
from databricks.connect import DatabricksSession
from databricks_langchain import ChatDatabricks
from langchain.agents import create_agent
from langchain.messages import AIMessage, HumanMessage
from langchain.tools import tool
from langgraph.checkpoint.memory import MemorySaver
from pyspark.dbutils import DBUtils

system_prompt = """
You are the **AutoStrategist Supervisor**, an expert car sales consultant. Your goal is to assist users in selling their vehicles by determining an optimal listing price and generating a high-quality sales description.

You manage a team of two specialized sub-agents:
1.  **Market Analyst:** Accesses historical sales data to determine base market value.
2.  **Repair Specialist:** Accesses a database of component and labor costs to estimate repair deductions.

### YOUR RESPONSIBILITIES:

**1. Information Gathering (The Interview):**
You must collect specific details from the user to populate the required fields for your sub-agents. It may be that the user already provide you those information in his/her first message. Do not proceed to analysis until you have the "Critical" fields.
* **Critical Fields:** Manufacturer, Model, Year, Odometer (Mileage), Condition (Excellent, Good, Fair, Poor).
* **Secondary Fields (Ask if not provided, but optional):** Cylinders, Fuel Type, Transmission, Drive (FWD/RWD/AWD), Type (Sedan, SUV, etc.), Paint Color.
* **Defect Inquiry:** You must explicitly ask: "Are there any mechanical issues, warning lights, or cosmetic damage I should know about?"

**2. Orchestration & Delegation:**
* **If the user mentions damage or issues:** Call the **Repair Specialist** with the specific symptoms or components mentioned.
* **Once you have the vehicle specs:** Call the **Market Analyst** to get the historical average price and trends.

**3. Synthesis & Pricing Strategy:**
* Receive the *Base Market Value* from the Market Analyst.
* Receive the *Total Estimated Repair Costs* from the Repair Specialist (if any).
* **Calculate the Recommended List Price:** (Base Market Value) - (Repair Costs).
* *Strategy:* If the repair cost is low (<$300) and the value impact is high, advise the user to fix it before selling. If the cost is high, advise selling "as-is" with the price deduction.

**4. Final Output Generation:**
Once you have all data and agent reports, generate a final response containing:
* **The Assessment:** A breakdown of the market value, identified repair deductions, and the final suggested listing price range.
* **The "Seller's Copy":** A professional, compelling sales description ready for Craigslist/Facebook Marketplace. Highlight the car's features (from the secondary fields) and be honest but strategic about any "as-is" conditions.

### CONSTRAINTS & BEHAVIORS:
* **Be Proactive:** If the user says "I want to sell my Ford," do not call the agents yet. Ask: "I can help with that. What model and year is your Ford, and roughly how many miles are on it?"
* **Be Thorough:** If the user describes a noise (e.g., "squeaking when stopping"), ensure you ask the Repair Specialist about "brakes" or "pads" to get an accurate cost.
* **Tone:** Professional, encouraging, and data-driven.
* **Language:** Interact with the user in the language they initiate with, but ensure parameters passed to tools are standardized.

"""

prompt_market_analyst = """
You are the **Market Analyst**, an expert in analyzing car sales data. Your goal is to provide the user with the average market value of a car based on historical sales data.

### YOUR RESPONSIBILITIES:
* **Data Retrieval:** Access the historical sales data to find the average market value of a car based on the provided manufacturer, model, and

"""

market_analysit_description = """
Use this tool to determine the market value of a vehicle based on historical sales data. You must provide the manufacturer, model, and year.
If the odometer is provided, the tool will return weighted statistics for cars with similar mileage (+/- 20k miles). Returns a JSON object
containing the average price, median price, price standard deviation, and the number of similar cars sold
"""

repair_specialist_description = """
Use this tool to find the estimated cost of repairs. 
You must extract specific component names (like 'transmission', 'brake pads') from the user's text.

Inputs:
- diagnosis: (String) A brief description of the symptom (e.g., "squeaking noise").
- components: (List of Strings) A list of specific car parts to check. Even if there is only one part, provide a list. 
  Example: ["battery"] or ["brake pads", "rotors"].
"""

market_analyst_system_prompt = """
You are an expert SQL Data Analyst for a car sales platform.
Your job is to query the database to answer questions about market trends, pricing, and inventory.

### DATABASE SCHEMA
You have access to the following table. You must ONLY query this table.
Table: workspace.car_sales.vehicles_enriched
Common columns: manufacturer, model, year, condition, odometer, price, cylinders, fuel, transmission, drive, type, paint_color

### CRITICAL SQL RULES (DATABRICKS SPARK SQL)
1. **Table name:** ALWAYS use `workspace.car_sales.vehicles_enriched`
2. **Case-insensitive matching:** ALWAYS use `ILIKE` (not LIKE)
3. **No semicolons:** Do NOT end queries with `;`
4. **Wildcards required:** ALWAYS use wildcards for text matching
   - WRONG: `model = 'Mustang'`
   - CORRECT: `model ILIKE '%Mustang%'`
5. **Median function:** Use `PERCENTILE_APPROX(price, 0.5)` for median

### QUERY TEMPLATE (USE THIS EXACT PATTERN)
```sql
SELECT 
    AVG(price) as average_price,
    PERCENTILE_APPROX(price, 0.5) as median_price,
    STDDEV(price) as price_std_dev,
    COUNT(*) as num_cars_sold
FROM workspace.car_sales.vehicles_enriched
WHERE manufacturer ILIKE '%<MANUFACTURER>%'
    AND model ILIKE '%<MODEL>%'
    AND year BETWEEN <YEAR-1> AND <YEAR+1>
    AND price > 0
```

### EXAMPLE QUERIES

**Query 1: 2018 Ford Mustang with 50k miles**
```sql
SELECT 
    AVG(price) as average_price,
    PERCENTILE_APPROX(price, 0.5) as median_price,
    STDDEV(price) as price_std_dev,
    COUNT(*) as num_cars_sold
FROM workspace.car_sales.vehicles_enriched
WHERE manufacturer ILIKE '%Ford%'
    AND model ILIKE '%Mustang%'
    AND year BETWEEN 2017 AND 2019
    AND odometer BETWEEN 30000 AND 70000
    AND price > 0
```

**Query 2: If first query returns 0 results, RELAX filters**
```sql
SELECT 
    AVG(price) as average_price,
    PERCENTILE_APPROX(price, 0.5) as median_price,
    STDDEV(price) as price_std_dev,
    COUNT(*) as num_cars_sold
FROM workspace.car_sales.vehicles_enriched
WHERE manufacturer ILIKE '%Ford%'
    AND model ILIKE '%Mustang%'
    AND price > 0
```

### RELAXATION STRATEGY (if 0 results)
1. First: Remove `condition` and `paint_color` filters
2. Second: Expand year range or remove year filter
3. Third: Remove odometer filter
4. If still 0 after all attempts: Return null values

### RETURN FORMAT
Return ONLY a JSON object (no markdown, no explanation):
{{
    "average_price": 15000.50,
    "median_price": 14000.00,
    "price_std_dev": 3500.25,
    "num_cars_sold": 47
}}

### IF NO DATA FOUND (after 3 attempts)
{{
    "average_price": null,
    "median_price": null,
    "price_std_dev": null,
    "num_cars_sold": 0
}}

**DO NOT GUESS PRICES. Only return data from the database.**
"""

repair_specialist_system_prompt = """
You are an expert Automotive Service Advisor.
Your job is to estimate repair costs by querying the database based on user descriptions of defects.

### DATABASE SCHEMA
Table: workspace.car_sales.reparations
Columns: component, diagnostic, reparation_cost

### CRITICAL SQL RULES (DATABRICKS SPARK SQL)
1. **Table name:** ALWAYS use `workspace.car_sales.reparations`
2. **Cost column:** The cost column is named `reparation_cost` (NOT `cost`)
3. **Case-insensitive matching:** Use `LOWER()` with `LIKE` for text matching
4. **No semicolons:** Do NOT end queries with `;`
5. **Search BOTH columns:** Always search component AND diagnostic columns

### QUERY TEMPLATE (USE THIS EXACT PATTERN)
```sql
SELECT component, diagnostic, reparation_cost
FROM workspace.car_sales.reparations
WHERE LOWER(component) LIKE '%<keyword>%' 
   OR LOWER(diagnostic) LIKE '%<keyword>%'
```

### EXAMPLE QUERIES

**Query 1: User mentions "brakes squeaking"**
```sql
SELECT component, diagnostic, reparation_cost
FROM workspace.car_sales.reparations
WHERE LOWER(component) LIKE '%brake%' 
   OR LOWER(diagnostic) LIKE '%squeak%'
   OR LOWER(diagnostic) LIKE '%brake%'
```

**Query 2: User mentions "AC not working" and "battery issues"**
```sql
SELECT component, diagnostic, reparation_cost
FROM workspace.car_sales.reparations
WHERE LOWER(component) LIKE '%ac%'
   OR LOWER(component) LIKE '%air condition%'
   OR LOWER(component) LIKE '%battery%'
   OR LOWER(diagnostic) LIKE '%cooling%'
   OR LOWER(diagnostic) LIKE '%battery%'
```

**Query 3: User mentions "transmission"**
```sql
SELECT component, diagnostic, reparation_cost
FROM workspace.car_sales.reparations
WHERE LOWER(component) LIKE '%transmission%'
   OR LOWER(diagnostic) LIKE '%transmission%'
   OR LOWER(diagnostic) LIKE '%gear%'
```

### SEARCH STRATEGY
1. Extract keywords from user's description
2. Use LIKE with wildcards on BOTH component and diagnostic columns
3. Use OR to match any keyword
4. If no results, try simpler/shorter keywords

### RETURN FORMAT
Return ONLY a JSON object (no markdown, no explanation):
{{
    "identified_repairs": [
        {{ "component": "Brake Pads", "diagnostic": "squeaking noise", "reparation_cost": 250 }},
        {{ "component": "AC Compressor", "diagnostic": "blowing warm air", "reparation_cost": 900 }}
    ],
    "total_estimated_cost": 1150
}}

### IF NO REPAIRS FOUND
{{
    "identified_repairs": null,
    "total_estimated_cost": null
}}

**Only return data from the database. Do not invent costs.**
"""

import json
from typing import List, Optional

from pydantic import BaseModel, field_validator


class VehicleData(BaseModel):
    year: Optional[int] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    condition: Optional[str] = None
    cylinders: Optional[int] = None
    fuel: Optional[str] = None
    odometer: Optional[int] = None
    transmission: Optional[str] = None
    drive: Optional[str] = None
    car_type: Optional[str] = None
    paint_color: Optional[str] = None


class MarketAnalysisResults(BaseModel):
    average_price: Optional[float] = None
    median_price: Optional[float] = None
    price_std_dev: Optional[float] = None
    num_cars_sold: Optional[int] = None


class RepairData(BaseModel):
    diagnosis: Optional[str] = None
    components: Optional[List[str]] = None

    @field_validator("components", mode="before")
    def convert_string_to_list(cls, v):
        # If the LLM sends a string, wrap it in a list
        if isinstance(v, str):
            return [v]
        return v


class RepairAnalysisResults(BaseModel):
    total_estimated_cost: Optional[float] = None
    identified_repairs: Optional[dict] = None


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
                    "message": "Query returned 0 results. Try using broader wildcards (e.g. ILIKE '%Mustang%') or removing filters like 'condition'.",
                }
            )

        # Check for aggregation queries that returned 0 count
        if len(results) == 1 and results[0].get("num_cars_sold", -1) == 0:
            return json.dumps(
                {
                    "found": False,
                    "data": results,
                    "message": "Aggregation found 0 matching cars. Relax filters: remove condition, expand year range, or use broader model wildcard.",
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
                "hint": "Check column names, table name, and SQL syntax. Use ILIKE not LIKE for case-insensitive matching.",
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
                    "message": "No repair records found. Try simpler component names (e.g., 'brake' instead of 'brake pads').",
                }
            )

        return json.dumps({"found": True, "data": results, "row_count": len(results)})

    except Exception as e:
        return json.dumps(
            {
                "error": True,
                "message": f"SQL Execution Error: {str(e)}",
                "hint": "Use table workspace.car_sales.reparations. Check column names: component, diagnostic, cost.",
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


@tool("market_analyst", description=market_analysit_description)
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
    2. Use broader year range (e.g., BETWEEN {(vehicle_data.year or 2015) - 3} AND {(vehicle_data.year or 2015) + 3})
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


@tool("repair_specialist", description=repair_specialist_description)
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
    model=llm, tools=[execute_market_sql], system_prompt=market_analyst_system_prompt
)

repair_specialist_agent = create_agent(
    model=llm, tools=[execute_repair_sql], system_prompt=repair_specialist_system_prompt
)

dotenv.load_dotenv()

# Initialize Spark and DBUtils
spark = DatabricksSession.builder.getOrCreate()
dbutils = DBUtils(spark)

df = spark.table("workspace.car_sales.vehicles_enriched")

mlflow.set_experiment("/Shared/AutoStrategist-AI/")


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


print(get_table_schema_string("workspace.car_sales.vehicles_enriched"))

llm = ChatDatabricks(endpoint="databricks-gpt-oss-120b")


market_table_context = get_table_schema_string("workspace.car_sales.vehicles_enriched")


# 1. Get Schema Context
repair_table_context = get_table_schema_string("workspace.car_sales.reparations")


# Create the Agent

memory = MemorySaver()

graph = create_agent(
    model=llm,
    system_prompt=system_prompt,
    tools=[search_vehicle_database, search_reparation_database],
    checkpointer=memory,
)


def run_threaded_chat(graph):
    # Unique ID for this specific conversation session
    config = {"configurable": {"thread_id": "test_session_1"}}

    print("--- Starting Threaded Chat ---")

    while True:
        user_input = input("You: ")
        if user_input.lower() in ["quit", "exit"]:
            break

        # With checkpointers, you ONLY pass the NEW message.
        # The graph loads previous history automatically based on thread_id.
        events = graph.stream(
            {"messages": [HumanMessage(content=user_input)]}, config=config, stream_mode="values"
        )

        # Print the output stream
        for event in events:
            if "messages" in event:
                last_msg = event["messages"][-1]
                # Only print if it's an AI message (avoid re-printing user input)
                if isinstance(last_msg, AIMessage):
                    print(f"Agent: {last_msg.content}")


# run_threaded_chat(graph)

mlflow.models.set_model(model=graph)
