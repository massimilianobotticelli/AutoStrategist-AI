"""
AutoStrategist AI - Streamlit Chat Interface
A simple chat interface for the car sales assistant agent.
"""

import os
import sys
from pathlib import Path

# Load environment variables FIRST, before any Databricks imports
import dotenv
dotenv.load_dotenv()

# Fix environment variable name if needed (DATABRICKS_HOSTNAME -> DATABRICKS_HOST)
if os.environ.get("DATABRICKS_HOSTNAME") and not os.environ.get("DATABRICKS_HOST"):
    os.environ["DATABRICKS_HOST"] = os.environ["DATABRICKS_HOSTNAME"]

# Add the agents directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "agents"))

import streamlit as st
from langchain.messages import AIMessage, HumanMessage

# Page configuration
st.set_page_config(
    page_title="AutoStrategist AI",
    page_icon="🚗",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# Custom CSS for chat styling
st.markdown("""
<style>
    .stApp {
        max-width: 900px;
        margin: 0 auto;
    }
    .chat-message {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    .user-message {
        background-color: #e3f2fd;
    }
    .assistant-message {
        background-color: #f5f5f5;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def load_agent():
    """Load the agent graph (cached to avoid reloading on each interaction)."""
    import dotenv
    from databricks.connect import DatabricksSession
    from databricks_langchain import ChatDatabricks
    from langchain.agents import create_agent
    from langgraph.checkpoint.memory import MemorySaver
    from prompts import system_prompt
    from tools import search_reparation_database, search_vehicle_database

    dotenv.load_dotenv()

    # Initialize LLM
    llm = ChatDatabricks(endpoint="databricks-gpt-oss-120b")

    # Create memory for conversation persistence
    memory = MemorySaver()

    # Create the agent
    graph = create_agent(
        model=llm,
        system_prompt=system_prompt,
        tools=[search_vehicle_database, search_reparation_database],
        checkpointer=memory,
    )

    return graph


def get_agent_response(graph, user_input: str, thread_id: str) -> str:
    """Get response from the agent."""
    config = {"configurable": {"thread_id": thread_id}}

    events = graph.stream(
        {"messages": [HumanMessage(content=user_input)]},
        config=config,
        stream_mode="values",
    )

    response = ""
    for event in events:
        if "messages" in event:
            last_msg = event["messages"][-1]
            if isinstance(last_msg, AIMessage):
                response = last_msg.content

    return response


def main():
    # Header
    st.title("🚗 AutoStrategist AI")
    st.markdown("*Your AI-powered car sales consultant*")
    st.markdown("---")

    # Initialize session state
    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "thread_id" not in st.session_state:
        import uuid
        st.session_state.thread_id = str(uuid.uuid4())

    if "agent_loaded" not in st.session_state:
        st.session_state.agent_loaded = False

    # Sidebar with info and controls
    with st.sidebar:
        st.header("ℹ️ About")
        st.markdown("""
        **AutoStrategist AI** helps you:
        - 💰 Determine optimal listing prices
        - 📝 Generate professional sales descriptions
        - 🔧 Estimate repair costs
        
        Just describe your vehicle and any issues!
        """)

        st.markdown("---")

        if st.button("🔄 New Conversation", use_container_width=True):
            import uuid
            st.session_state.messages = []
            st.session_state.thread_id = str(uuid.uuid4())
            st.rerun()

        st.markdown("---")
        st.caption(f"Session: {st.session_state.thread_id[:8]}...")

    # Load agent
    try:
        with st.spinner("Loading AI agent..."):
            graph = load_agent()
            st.session_state.agent_loaded = True
    except Exception as e:
        st.error(f"❌ Failed to load agent: {str(e)}")
        st.info("Make sure you have configured your Databricks connection and environment variables.")
        return

    # Display welcome message if no messages yet
    if not st.session_state.messages:
        st.info("""
        👋 **Welcome to AutoStrategist AI!**
        
        I'm here to help you sell your car. Tell me about your vehicle and I'll:
        - Analyze market data to suggest a competitive price
        - Identify any repair costs that might affect value
        - Create a professional listing description
        
        **Example:** "I want to sell my 2018 Ford Mustang with 45,000 miles in good condition. 
        It has a small dent on the rear bumper and the brakes squeak a bit."
        """)

    # Display chat history
    for message in st.session_state.messages:
        role = message["role"]
        content = message["content"]

        if role == "user":
            with st.chat_message("user", avatar="👤"):
                st.markdown(content)
        else:
            with st.chat_message("assistant", avatar="🚗"):
                st.markdown(content)

    # Chat input
    if user_input := st.chat_input("Describe your vehicle or ask a question..."):
        # Add user message to history
        st.session_state.messages.append({"role": "user", "content": user_input})

        # Display user message
        with st.chat_message("user", avatar="👤"):
            st.markdown(user_input)

        # Get and display assistant response
        with st.chat_message("assistant", avatar="🚗"):
            with st.spinner("Analyzing..."):
                try:
                    response = get_agent_response(
                        graph, user_input, st.session_state.thread_id
                    )
                    st.markdown(response)

                    # Add assistant message to history
                    st.session_state.messages.append(
                        {"role": "assistant", "content": response}
                    )
                except Exception as e:
                    error_msg = f"Sorry, I encountered an error: {str(e)}"
                    st.error(error_msg)
                    st.session_state.messages.append(
                        {"role": "assistant", "content": error_msg}
                    )


if __name__ == "__main__":
    main()
