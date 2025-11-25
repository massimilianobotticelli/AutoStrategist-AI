import mlflow
from databricks.connect import DatabricksSession
from databricks_langchain import ChatDatabricks
from langchain.agents import create_agent
from langchain.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from prompts import system_prompt
from pyspark.dbutils import DBUtils
from tools import search_reparation_database, search_vehicle_database

import dotenv
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


run_threaded_chat(graph)
