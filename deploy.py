
"""MLflow Model Deployment Module.

This module provides functions for logging, registering, and deploying
LangChain models to Databricks using MLflow. It supports the full lifecycle
of model deployment including experiment tracking, model registration in
Unity Catalog, and endpoint deployment.

Typical usage:
    1. Log an experiment with `log_experiment_lc()`
    2. Register the model with `register_model()`
    3. Set an alias with `set_model_alias()`
    4. Deploy to an endpoint with `deploy_model()`
"""

import os
from typing import Optional

import mlflow
from databricks import agents
from databricks.sdk import WorkspaceClient
from mlflow import MlflowClient
from mlflow.models import infer_signature
from mlflow.models.resources import DatabricksServingEndpoint


def upload_to_volume(
    local_file_path: str,
    volume_path: str,
    overwrite: bool = True,
) -> str:

    # Initialize Databricks Workspace Client
    w = WorkspaceClient()

    # Get the filename from local path
    filename = os.path.basename(local_file_path)

    # Destination path in the volume
    dest_path = f"{volume_path}/{filename}"

    # Read local file and upload
    with open(local_file_path, "rb") as f:
        file_content = f.read()

    # Upload to volume using the files API
    w.files.upload(dest_path, file_content, overwrite=overwrite)

    print(f"Uploaded {local_file_path} to {dest_path}")
    return dest_path



def log_experiment_lc(
    llm_endpoint_name: str,
    lc_model_path: str,
    experiment_path: str,
    experiment_name: str,
    run_name: str,
    code_paths: Optional[list[str]] = None,
):
    """
    Log a LangChain model experiment to MLflow.

    Creates an MLflow experiment (if it doesn't exist) and logs a LangChain
    model with its dependencies and signature.

    Args:
        llm_endpoint_name: Name of the Databricks serving endpoint for the LLM.
        lc_model_path: Path to the LangChain model Python file.
        experiment_path: Base path for the MLflow experiment (e.g., '/Shared/models/').
        experiment_name: Name of the experiment to create or use.
        run_name: Name for this specific MLflow run.
        code_paths: Optional list of paths to Python files/directories that
            the model depends on. These are bundled with the logged model
            so imports can be resolved at load time.

    Returns:
        mlflow.models.model.ModelInfo: Information about the logged model,
            including the model URI. An additional `_runs_uri` attribute is
            added for compatibility with model loading.

    Example:
        >>> logged_info = log_experiment_lc(
        ...     llm_endpoint_name="databricks-gpt-oss-120b",
        ...     lc_model_path="agents/workflow.py",
        ...     experiment_path="/Shared/models/",
        ...     experiment_name="my_experiment",
        ...     run_name="run_001",
        ...     code_paths=["my_package"],
        ... )
        >>> print(logged_info.model_uri)
    """

    # Construct full experiment path
    full_experiment_name = os.path.join(experiment_path, experiment_name)

    # Create experiment if it doesn't exist, then set as active
    if mlflow.get_experiment_by_name(full_experiment_name) is None:
        mlflow.create_experiment(name=full_experiment_name)
    mlflow.set_experiment(full_experiment_name)

    # Define Databricks resources the model depends on
    resources = [DatabricksServingEndpoint(llm_endpoint_name)]

    # Define model signature using Agent Framework's ChatCompletionRequest format
    # Input: 'messages' array with role/content pairs
    # Output: Simple string response
    signature = infer_signature(
        model_input={"messages": [{"role": "user", "content": "Sample input"}]},
        model_output="Sample output response",
    )

    # Log the LangChain model to MLflow
    with mlflow.start_run(run_name=run_name) as run:
        logged_chain_info = mlflow.langchain.log_model(
            lc_model=lc_model_path,
            signature=signature,
            name="model",
            resources=resources,
            code_paths=code_paths,
        )
        runs_uri = f"runs:/{run.info.run_id}/model"

    print(f"Logged Model URI: {logged_chain_info.model_uri}")
    print(f"Runs URI (for loading): {runs_uri}")

    # Store runs_uri for downstream compatibility
    logged_chain_info._runs_uri = runs_uri

    return logged_chain_info


def register_model(model_uri: str, uc_model_path: str):
    """
    Register a model in the MLflow Model Registry (Unity Catalog).

    Args:
        model_uri: URI of the model to register (e.g., 'runs:/<run_id>/model').
        uc_model_path: Full Unity Catalog path for the model
            (e.g., 'catalog.schema.model_name').

    Returns:
        mlflow.entities.model_registry.ModelVersion: Registered model version
            information including version number and status.

    Example:
        >>> model_info = register_model(
        ...     "runs:/abc123/model",
        ...     "workspace.my_schema.my_model"
        ... )
        >>> print(f"Registered version: {model_info.version}")
    """
    return mlflow.register_model(model_uri=model_uri, name=uc_model_path)

def set_model_alias(uc_model_path: str, version: int, alias: str) -> None:
    """
    Set an alias on a registered model version.

    Aliases provide human-readable references to specific model versions,
    useful for deployment workflows (e.g., 'champion', 'challenger', 'production').

    Args:
        uc_model_path: Full Unity Catalog path (e.g., 'catalog.schema.model').
        version: Model version number to alias.
        alias: Alias name to assign (e.g., 'champion', 'production').

    Example:
        >>> set_model_alias("workspace.sales.my_model", version=3, alias="champion")
        Set alias 'champion' on workspace.sales.my_model version 3
    """
    client = MlflowClient()
    client.set_registered_model_alias(
        name=uc_model_path,
        alias=alias,
        version=version,
    )
    print(f"Set alias '{alias}' on {uc_model_path} version {version}")


def deploy_model(
    uc_model_path: str,
    model_version: int,
    tags: dict[str, str],
    endpoint_name: str,
    scale_to_zero: bool = True,
):
    """
    Deploy a model to a Databricks serving endpoint.

    Creates or updates a Databricks model serving endpoint with the specified
    model version from Unity Catalog.

    Args:
        uc_model_path: Full Unity Catalog path to the model
            (e.g., 'catalog.schema.model_name').
        model_version: Version number of the model to deploy.
        tags: Metadata tags for the deployment (e.g., {'project': 'sales'}).
        endpoint_name: Name for the serving endpoint.
        scale_to_zero: If True, endpoint scales to zero replicas when idle,
            reducing costs. Defaults to True.

    Returns:
        Deployment information from Databricks agents.deploy().

    Example:
        >>> deploy_model(
        ...     uc_model_path="workspace.sales.car_model",
        ...     model_version=1,
        ...     tags={"project": "car_sales", "env": "prod"},
        ...     endpoint_name="car-sales-endpoint",
        ... )
    """
    
    deploy_info = agents.deploy(
        model_name=uc_model_path,
        model_version=model_version,
        scale_to_zero=scale_to_zero,
        tags=tags,
        endpoint_name=endpoint_name,
    )

    return deploy_info

# =============================================================================
# Configuration Constants
# =============================================================================

# LLM Configuration
DEFAULT_LLM_ENDPOINT = "databricks-gpt-oss-120b"

# Model Paths
DEFAULT_LC_MODEL_PATH = "autostrategist_ai/agents/workflow.py"
DEFAULT_CODE_PATHS = ["autostrategist_ai"]

# MLflow Experiment Configuration
DEFAULT_EXPERIMENT_PATH = "/Shared/models/"
DEFAULT_EXPERIMENT_NAME = "car_sales_workflow_experiment"
DEFAULT_RUN_NAME = "car_sales_workflow_run"

# Unity Catalog Configuration
DEFAULT_UC_MODEL_PATH = "workspace.car_sales.car_sales_workflow_model"
DEFAULT_ENDPOINT_NAME = "car-sales-workflow-endpoint"
DEFAULT_TAGS = {"project": "car_sales_workflow", "owner": "data_team"}

# Volume Configuration
DEFAULT_VOLUME_PATH = "/Volumes/workspace/car_sales/artifactory"
DEFAULT_WHEEL_PATH = "./dist/autostrategist_ai-0.1.0-py3-none-any.whl"

SERVING_ENDPOINT_ENABLED = False  # Set to True to enable deployment


def main():
    """Execute the full model deployment pipeline."""
    # Step 1: Log the experiment and model
    logged_chain_info = log_experiment_lc(
        llm_endpoint_name=DEFAULT_LLM_ENDPOINT,
        lc_model_path=DEFAULT_LC_MODEL_PATH,
        experiment_path=DEFAULT_EXPERIMENT_PATH,
        experiment_name=DEFAULT_EXPERIMENT_NAME,
        run_name=DEFAULT_RUN_NAME,
        code_paths=DEFAULT_CODE_PATHS,
    )

    # Step 2: Register the model in Unity Catalog
    model_info = register_model(
        model_uri=logged_chain_info.model_uri,
        uc_model_path=DEFAULT_UC_MODEL_PATH,
    )
    print(f"Registered model version: {model_info.version}")

    # Step 3: Set model alias (optional - for staged rollouts)
    set_model_alias(
        uc_model_path=DEFAULT_UC_MODEL_PATH,
        version=model_info.version,
        alias="challenger",
    )

    if not SERVING_ENDPOINT_ENABLED:
        print("Deployment disabled because of Databricks Free Verson limitations.")
    
    else:
        # Step 4: Deploy to serving endpoint
        deployment_info = deploy_model(
            uc_model_path=DEFAULT_UC_MODEL_PATH,
            model_version=model_info.version,
            tags=DEFAULT_TAGS,
            endpoint_name=DEFAULT_ENDPOINT_NAME,
            scale_to_zero=True,
        )
        print(f"Deployment complete: {deployment_info}")

    print("Model deployment pipeline completed successfully.")


if __name__ == "__main__":
    main()
    # Upload wheel file to volume
    # upload_to_volume(
    #     local_file_path="./dist/autostrategist_ai-0.1.0-py3-none-any.whl",
    #     volume_path="/Volumes/workspace/car_sales/artifactory"
    # )
  