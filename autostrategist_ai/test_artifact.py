"""
Test script to load and invoke an MLflow logged LangChain model.
"""

import mlflow

# Set tracking URI to Databricks (required when running locally)
mlflow.set_tracking_uri("databricks")

import dotenv

dotenv.load_dotenv()

# Option 1: Load from a specific run URI
# Format: runs:/<run_id>/<artifact_path>
# The artifact path is typically "model" (not "artifacts")
MODEL_URI = "runs:/039aa6e3cf104430b6aed6bc41818ba1/model"

# Option 2: Load from a registered model (if registered)
# MODEL_URI = "models:/car_sales_workflow_model/1"

# Option 3: If the model was logged with a custom artifact path, check MLflow UI
# MODEL_URI = "runs:/4826ae84699f4f9793f7f6c9f7cbb248/chain"


def test_model():
    """Load the MLflow model and run a test query."""

    print(f"Loading model from: {MODEL_URI}")

    # Load the model as a LangChain object
    loaded_model = mlflow.langchain.load_model(MODEL_URI)

    print("Model loaded successfully!")
    print(f"Model type: {type(loaded_model)}")

    # Test input - adjust based on your agent's expected input format
    test_input = {"messages": [{"role": "user", "content": "I want to sell my Ford Mustang."}]}

    # Invoke the model
    print("\n--- Running test query ---")
    response = loaded_model.invoke(test_input)

    print("\n--- Response ---")
    print(response)

    return response


def test_model_with_pyfunc():
    """
    Alternative: Load as a generic PyFunc model.
    This is useful for serving and provides a consistent interface.
    """

    print(f"Loading model as PyFunc from: {MODEL_URI}")

    loaded_model = mlflow.pyfunc.load_model(MODEL_URI)

    print("Model loaded successfully!")

    # PyFunc models expect a DataFrame or dict input
    import pandas as pd

    test_input = pd.DataFrame(
        {"messages": [[{"role": "user", "content": "What vehicles do you have available?"}]]}
    )

    print("\n--- Running test query (PyFunc) ---")
    response = loaded_model.predict(test_input)

    print("\n--- Response ---")
    print(response)

    return response


if __name__ == "__main__":
    # Choose which method to test
    print("=" * 50)
    print("Testing MLflow LangChain Model")
    print("=" * 50)

    # Test using native LangChain loading
    test_model()

    # Uncomment to test PyFunc loading
    # test_model_with_pyfunc()
