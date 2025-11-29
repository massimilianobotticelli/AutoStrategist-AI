# AutoStrategist-AI

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![Databricks](https://img.shields.io/badge/Databricks-Enabled-orange.svg)](https://databricks.com/)

An AI-powered platform for optimizing second-hand car sales, built on Databricks. Features an intelligent chat agent that provides market analysis, repair cost estimation, and professional sales descriptions.

## 🎯 Features

- **🤖 AI Sales Consultant**: LangChain-based agent that interviews users about their vehicle
- **📊 Market Analysis**: Real-time price estimation based on historical sales data
- **🔧 Repair Cost Estimation**: Automatic deduction calculation for vehicle defects
- **📝 Sales Copy Generation**: Professional listing descriptions for marketplaces
- **💬 Streamlit Chat Interface**: User-friendly web application
- **🚀 MLflow Integration**: Model tracking, registration, and deployment via Unity Catalog
- **📦 Databricks Apps**: Production-ready deployment as a Databricks App

## 🏗️ Architecture

This project uses a modern data & AI architecture on Databricks:

- **Data Pipeline**: Medallion architecture (Bronze → Silver → Gold)
- **AI Agent**: LangChain with specialized tools (Market Analyst, Repair Specialist)
- **LLM**: Databricks Foundation Models (`databricks-gpt-oss-120b`)
- **Model Registry**: MLflow with Unity Catalog integration
- **Deployment**: Databricks Asset Bundles (DABs) + Databricks Apps
- **Compute**: Databricks Connect + Serverless Compute

## 🚀 Getting Started

### Prerequisites

- Python 3.11
- Poetry (for dependency management)
- Databricks workspace with:
  - Serverless compute enabled (recommended) OR a running cluster
  - Unity Catalog enabled
  - Personal Access Token
- Kaggle API credentials (for data ingestion)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/massimilianobotticelli/AutoStrategist-AI.git
   cd AutoStrategist-AI
   ```

2. **Install dependencies with Poetry**
   ```bash
   poetry install
   ```

3. **Configure environment variables**
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` with your credentials:
   ```env
   # Databricks Configuration (REQUIRED)
   DATABRICKS_HOST=https://your-workspace.cloud.databricks.com
   DATABRICKS_TOKEN=your-databricks-token
   
   # Kaggle API (for data ingestion)
   KAGGLE_USERNAME=your-kaggle-username
   KAGGLE_KEY=your-kaggle-api-key
   ```

4. **Configure Databricks CLI**
   ```bash
   databricks configure --token
   # Enter your Databricks workspace URL and personal access token
   ```

5. **Update Databricks Asset Bundle configuration**
   ```bash
   cp databricks.example.yml databricks.yml
   # Edit databricks.yml and update workspace.host with your Databricks URL
   ```

6. **Deploy the data pipeline**
   ```bash
   databricks bundle validate
   databricks bundle deploy
   databricks bundle run ingest_kaggle_data
   ```

### Running the Application

**Option 1: Local Development (Streamlit)**
```bash
poetry run streamlit run app/app.py
```

**Option 2: Deploy as Databricks App**
```bash
databricks bundle deploy
# The app will be available at your Databricks workspace
```

## 📁 Project Structure

```
AutoStrategist-AI/
├── databricks.yml              # Databricks Asset Bundle configuration
├── databricks.example.yml      # Example DABs template
├── pyproject.toml              # Poetry dependencies & project config
├── deploy.py                   # MLflow model deployment utilities
├── .env.example                # Environment variables template
│
├── app/                        # Databricks App (Streamlit)
│   ├── app.py                  # Main Streamlit chat interface
│   ├── app.yaml                # Databricks App configuration
│   └── requirements.txt        # App-specific dependencies
│
├── autostrategist_ai/          # Main Python package
│   ├── __init__.py
│   ├── agents/                 # AI Agent components
│   │   ├── workflow.py         # Main agent orchestration
│   │   ├── tools.py            # LangChain tools (SQL execution, sub-agents)
│   │   ├── prompts.py          # System prompts for all agents
│   │   └── data_structures.py  # Pydantic models (VehicleData, RepairData)
│   │
│   └── ingestion/              # Data pipeline scripts
│       ├── load_data.py        # Download from Kaggle
│       ├── ingest_data.py      # Ingest to Bronze layer
│       ├── prepare_data.py     # Transform to Silver layer
│       ├── car_models_clean.py # Clean car model names
│       ├── enrich_data.py      # Enrich to Gold layer
│       ├── reparation_data.py  # Load repair costs data
│       ├── reparation.csv      # Repair costs reference data
│       └── prompts.py          # Prompts for data enrichment
│
├── resources/                  # Databricks Asset Bundle resources
│   ├── app.yml                 # Databricks App deployment config
│   ├── deploy.yml              # Model deployment job config
│   └── ingestion.yml           # Data pipeline job definitions
│
└── development/                # Development notebooks
    ├── extract_details_dev.ipynb
    └── prepare_dev.ipynb
```

## 🤖 Agent Architecture

The AutoStrategist agent uses a **tool-based pattern** with specialized capabilities:

```
┌─────────────────────────────────────────────────────┐
│              AutoStrategist Supervisor              │
│  (Interviews user, orchestrates, generates output)  │
└─────────────────┬───────────────────┬───────────────┘
                  │                   │
    ┌─────────────▼─────────┐ ┌───────▼─────────────┐
    │    Market Analyst     │ │  Repair Specialist  │
    │    (SQL Tool)         │ │     (SQL Tool)      │
    │ (vehicles_enriched)   │ │   (reparations)     │
    └───────────────────────┘ └─────────────────────┘
```

### Agent Tools

| Tool | Description |
|------|-------------|
| `search_vehicle_database` | Queries historical sales data for market analysis |
| `search_reparation_database` | Looks up repair component costs |

### Data Tables

| Table | Description |
|-------|-------------|
| `workspace.car_sales.vehicles_enriched` | Historical car sales with prices, specs |
| `workspace.car_sales.reparations` | Repair components and costs |

## 🚀 Deployment

### Model Deployment with MLflow

The project uses MLflow for model lifecycle management:

```python
# Log and register the model
from deploy import log_experiment_lc, register_model, set_model_alias

# Log experiment
run_id = log_experiment_lc(graph, "experiment_name")

# Register to Unity Catalog
register_model(run_id, "workspace.car_sales.car_sales_workflow_model")

# Set alias for production
set_model_alias("workspace.car_sales.car_sales_workflow_model", "champion")
```

### Databricks Apps Deployment

Deploy the Streamlit app as a Databricks App:

```bash
# Validate and deploy
databricks bundle validate
databricks bundle deploy

# The app configuration is in app/app.yaml
```

### ⚠️ Important: Building and Uploading the Wheel Package

> **Note for Databricks Community Edition / Free Tier Users:** Model Serving Endpoints are not available on the free tier. This project uses a workaround where the agent is loaded directly from the `autostrategist_ai` package (installed via a wheel file) instead of downloading from a Unity Catalog registered model.

The Databricks App requires the `autostrategist_ai` package to be available as a wheel file in a Unity Catalog Volume. You must build and upload the wheel manually:

1. **Build the wheel package**
   ```bash
   poetry build
   ```

2. **Upload the wheel to the Databricks Volume**
   ```bash
   databricks fs cp ./dist/autostrategist_ai-0.1.0-py3-none-any.whl dbfs:/Volumes/workspace/car_sales/artifactory/
   ```

3. **Verify the upload**
   ```bash
   databricks fs ls dbfs:/Volumes/workspace/car_sales/artifactory/
   ```

The app uses the `WHEELS_MODULE` environment variable (configured in `app/app.yaml`) to determine whether to load the agent from the wheel package or from MLflow. When set to `"true"`, the app imports the agent directly from the installed package.

## 🛠️ Development Workflow

### Working with Databricks Asset Bundles

```bash
# Validate configuration
databricks bundle validate

# Deploy to Databricks
databricks bundle deploy

# Run the data ingestion pipeline
databricks bundle run ingest_kaggle_data

# Run model deployment job
databricks bundle run log_register_deploy
```

### Local Development

```bash
# Run the Streamlit app locally
poetry run streamlit run app/app.py

# The app will connect to your Databricks workspace
# using credentials from .env or databricks CLI config
```

### Code Formatting

```bash
poetry run black autostrategist_ai/
poetry run isort autostrategist_ai/
```

## 📊 Data Pipeline

The pipeline follows the medallion architecture:

| Stage | Script | Description |
|-------|--------|-------------|
| **Load** | `load_data.py` | Downloads Kaggle Craigslist Cars dataset |
| **Bronze** | `ingest_data.py` | Raw data ingestion |
| **Silver** | `prepare_data.py` | Cleaning & standardization |
| **Clean** | `car_models_clean.py` | Normalize car model names |
| **Gold** | `enrich_data.py` | Enrichment & aggregation |
| **Repairs** | `reparation_data.py` | Load repair cost reference data |

## 🔧 Troubleshooting

### "Cluster id or serverless are required"

Ensure you have serverless compute enabled or specify a cluster. For serverless:
```env
DATABRICKS_SERVERLESS_COMPUTE_ID=auto
```

### Connection Issues

1. Ensure your Databricks workspace is accessible
2. Verify `DATABRICKS_HOST` and `DATABRICKS_TOKEN` are correct
3. Check that your token has not expired
4. For local development, ensure `databricks configure` was run successfully

### Model Loading Issues

If the Streamlit app can't load the model:
1. Verify the model exists in Unity Catalog: `workspace.car_sales.car_sales_workflow_model`
2. Check the "champion" alias is set
3. Ensure your token has permissions to access the model

## 🔐 Security

- Store credentials in Databricks Secrets for production
- Use `.env` for local development (never commit!)
- Keep `.databrickscfg` secure and never commit to version control
- The app uses Unity Catalog for secure model access

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Databricks](https://databricks.com/) for the lakehouse platform
- [LangChain](https://langchain.com/) for the agent framework
- [MLflow](https://mlflow.org/) for model lifecycle management
- [Streamlit](https://streamlit.io/) for the chat interface
- [Kaggle](https://www.kaggle.com/) for the Craigslist Cars dataset

## 🔮 Future Development

- **Automated wheel deployment**: Create a script or GitHub Action to automatically build and upload the wheel package to the Databricks Volume on each release
- **Model Serving Endpoint**: For users with Databricks paid tiers, add support for deploying the agent as a Model Serving Endpoint
