"""AutoStrategist AI - Streamlit Chat Interface.

A conversational chat interface for the car sales assistant agent.
Loads the production 'champion' model from MLflow Unity Catalog to provide:
- Market value estimates for vehicles
- Professional sales listing descriptions
- Repair cost analysis

Usage:
    streamlit run app/streamlit_app.py
"""

import os
from typing import Any

import dotenv
import streamlit as st

# Load environment variables before any Databricks/MLflow imports
dotenv.load_dotenv()

# Normalize Databricks host environment variable
if os.environ.get("DATABRICKS_HOSTNAME") and not os.environ.get("DATABRICKS_HOST"):
    os.environ["DATABRICKS_HOST"] = os.environ["DATABRICKS_HOSTNAME"]

# =============================================================================
# Configuration
# =============================================================================

# Unity Catalog model configuration
UC_MODEL_PATH = "workspace.car_sales.car_sales_workflow_model"
MODEL_ALIAS = "champion"

# UI Configuration
PAGE_TITLE = "AutoStrategist AI"
PAGE_ICON = "🚗"
USER_AVATAR = "👤"
ASSISTANT_AVATAR = "🚗"

# Page setup
st.set_page_config(
    page_title=PAGE_TITLE,
    page_icon=PAGE_ICON,
    layout="centered",
    initial_sidebar_state="collapsed",
)

# =============================================================================
# Content Strings
# =============================================================================

WELCOME_MESSAGE = """
👋 **Welcome to AutoStrategist AI!**

I'm here to help you sell your car. Tell me about your vehicle and I'll:
- Analyze market data to suggest a competitive price
- Identify any repair costs that might affect value
- Create a professional listing description

**Example:** "I want to sell my 2018 Ford Mustang with 45,000 miles in good condition.
It has a small dent on the rear bumper and the brakes squeak a bit."
"""

ABOUT_TEXT = """
**AutoStrategist AI** helps you:
- 💰 Determine optimal listing prices
- 📝 Generate professional sales descriptions
- 🔧 Estimate repair costs

Just describe your vehicle and any issues!
"""


# =============================================================================
# Model Loading
# =============================================================================


@st.cache_resource
def load_agent() -> Any:
    """Load the champion model from MLflow Unity Catalog.

    Uses Streamlit's cache_resource to load the model once and reuse it
    across all user sessions, improving performance and reducing latency.

    Returns:
        The loaded LangChain model from MLflow.

    Raises:
        Exception: If the model fails to load from Unity Catalog.
    """
    import mlflow

    model_uri = f"models:/{UC_MODEL_PATH}@{MODEL_ALIAS}"

    try:
        model = mlflow.langchain.load_model(model_uri)
        st.sidebar.success(f"✅ Loaded model: `{MODEL_ALIAS}`")
        return model
    except Exception as e:
        st.error(f"Failed to load champion model from {model_uri}: {e}")
        raise


# =============================================================================
# Response Handling
# =============================================================================


def _extract_ai_response(response: Any) -> str:
    """Extract the AI response content from various response formats.

    The MLflow LangChain model can return responses in different formats:
    - Raw string
    - Dict with 'messages' list containing LangChain message objects
    - Single message object with 'content' attribute
    - Dict with direct 'content' key

    Args:
        response: The raw response from model.invoke().

    Returns:
        The extracted response text as a string.
    """
    # Direct string response
    if isinstance(response, str):
        return response

    # Dict with 'messages' list (LangChain agent format)
    if isinstance(response, dict) and "messages" in response:
        for msg in reversed(response["messages"]):
            if hasattr(msg, "content") and msg.__class__.__name__ == "AIMessage":
                return msg.content
        # Fallback: last message with content
        for msg in reversed(response["messages"]):
            if hasattr(msg, "content"):
                return msg.content

    # Single message object
    if hasattr(response, "content"):
        return response.content

    # Dict with direct content key
    if isinstance(response, dict) and "content" in response:
        return response["content"]

    return str(response)


def get_agent_response(model: Any, user_input: str) -> str:
    """Get a response from the champion model.

    Builds the conversation history from session state, appends the new
    user input, and invokes the model to get a response.

    Args:
        model: The loaded MLflow LangChain model.
        user_input: The user's message text.

    Returns:
        The model's response as a string.
    """
    # Build conversation history in ChatCompletionRequest format
    messages = [
        {"role": msg["role"], "content": msg["content"]}
        for msg in st.session_state.messages
    ]
    messages.append({"role": "user", "content": user_input})

    # Invoke model and extract response
    response = model.invoke({"messages": messages})
    return _extract_ai_response(response)


# =============================================================================
# UI Components
# =============================================================================


def _init_session_state() -> None:
    """Initialize Streamlit session state variables."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "agent_loaded" not in st.session_state:
        st.session_state.agent_loaded = False


def _render_sidebar() -> None:
    """Render the sidebar with app info and controls."""
    with st.sidebar:
        st.header("ℹ️ About")
        st.markdown(ABOUT_TEXT)
        st.markdown("---")

        if st.button("🔄 New Conversation", use_container_width=True):
            st.session_state.messages = []
            st.rerun()

        st.markdown("---")


def _render_chat_history() -> None:
    """Display the conversation history."""
    for message in st.session_state.messages:
        avatar = USER_AVATAR if message["role"] == "user" else ASSISTANT_AVATAR
        with st.chat_message(message["role"], avatar=avatar):
            st.markdown(message["content"])


def _handle_user_input(model: Any) -> None:
    """Process user input and generate assistant response.

    Args:
        model: The loaded LangChain model.
    """
    if user_input := st.chat_input("Describe your vehicle or ask a question..."):
        # Add and display user message
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user", avatar=USER_AVATAR):
            st.markdown(user_input)

        # Generate and display assistant response
        with st.chat_message("assistant", avatar=ASSISTANT_AVATAR):
            with st.spinner("Analyzing..."):
                try:
                    response = get_agent_response(model, user_input)
                    st.markdown(response)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response,
                    })
                except Exception as e:
                    error_msg = f"Sorry, I encountered an error: {str(e)}"
                    st.error(error_msg)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": error_msg,
                    })

            st.rerun()


# =============================================================================
# Main Application
# =============================================================================


def main() -> None:
    """Run the AutoStrategist AI chat application."""
    # Header
    st.title(f"{PAGE_ICON} {PAGE_TITLE}")
    st.markdown("*Your AI-powered car sales consultant*")
    st.markdown("---")

    # Initialize state and render sidebar
    _init_session_state()
    _render_sidebar()

    # Load the champion model
    try:
        with st.spinner("Loading AI agent..."):
            model = load_agent()
            st.session_state.agent_loaded = True
    except Exception as e:
        st.error(f"❌ Failed to load agent: {str(e)}")
        st.info(
            "Make sure you have configured your Databricks connection "
            "and environment variables."
        )
        return

    # Show welcome message for new conversations
    if not st.session_state.messages:
        st.info(WELCOME_MESSAGE)

    # Render chat UI
    _render_chat_history()
    _handle_user_input(model)


if __name__ == "__main__":
    main()
