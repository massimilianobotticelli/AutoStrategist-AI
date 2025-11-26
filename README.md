# AutoStrategist-AI

An AI-powered platform for optimizing second-hand car sales, built on Databricks. Features an intelligent chat agent that provides market analysis, repair cost estimation, and professional sales descriptions.

## 🎯 Features

- **🤖 AI Sales Consultant**: LangGraph-based agent that interviews users about their vehicle
- **📊 Market Analysis**: Real-time price estimation based on historical sales data
- **🔧 Repair Cost Estimation**: Automatic deduction calculation for vehicle defects
- **📝 Sales Copy Generation**: Professional listing descriptions for marketplaces
- **💬 Streamlit Chat Interface**: User-friendly web application

## 🏗️ Architecture

This project uses a modern data & AI architecture on Databricks:

- **Data Pipeline**: Medallion architecture (Bronze → Silver → Gold)
- **AI Agent**: LangGraph with specialized sub-agents (Market Analyst, Repair Specialist)
- **LLM**: Databricks Foundation Models (`databricks-gpt-oss-120b`)
- **Compute**: Databricks Connect + Serverless/Cluster

## 🚀 Getting Started

### Prerequisites

- Python 3.11+
- Poetry (for dependency management)
- Databricks workspace with:
  - A running cluster OR serverless compute enabled
  - Personal Access Token
- Kaggle API credentials (for data ingestion)

### Installation

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
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

   > **Finding your Cluster ID**: Go to Databricks workspace → Compute → Select your cluster → The ID is in the URL or under "Advanced Options"

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

**Start the Streamlit chat interface:**
```bash
poetry run streamlit run src/app/streamlit_app.py
```

**Or run the CLI agent directly:**
```bash
poetry run python src/agents/workflow.py
```

## 📁 Project Structure

```
AutoStrategist-AI/
├── databricks.yml              # Databricks Asset Bundle configuration
├── databricks.example.yml      # Example DABs template
├── pyproject.toml              # Poetry dependencies & project config
├── .env.example                # Environment variables template
│
├── resources/
│   ├── ingestion.yml           # DABs job definitions for data pipeline
│   └── ingestion-local.yml     # Local development job config
│
├── src/
│   ├── agents/                 # AI Agent components
│   │   ├── workflow.py         # Main agent orchestration (CLI)
│   │   ├── tools.py            # LangChain tools (SQL execution, sub-agents)
│   │   ├── prompts.py          # System prompts for all agents
│   │   ├── data_structures.py  # Pydantic models (VehicleData, RepairData)
│   │   └── workflow.ipynb      # Interactive notebook version
│   │
│   ├── app/
│   │   └── streamlit_app.py    # Streamlit chat interface
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
├── development/                # Development notebooks
│   ├── extract_details_dev.ipynb
│   └── prepare_dev.ipynb
│
└── 04_final_clean.ipynb        # Final data cleaning notebook
```

## 🤖 Agent Architecture

The AutoStrategist agent uses a **supervisor pattern** with specialized sub-agents:

```
┌─────────────────────────────────────────────────────┐
│              AutoStrategist Supervisor              │
│  (Interviews user, orchestrates, generates output)  │
└─────────────────┬───────────────────┬───────────────┘
                  │                   │
    ┌─────────────▼─────────┐ ┌───────▼─────────────┐
    │    Market Analyst     │ │  Repair Specialist  │
    │ (SQL: vehicles_enriched) │ │ (SQL: reparations)   │
    └───────────────────────┘ └─────────────────────┘
```

### Data Tables

| Table | Description |
|-------|-------------|
| `workspace.car_sales.vehicles_enriched` | Historical car sales with prices, specs |
| `workspace.car_sales.reparations` | Repair components and costs |

## 🛠️ Development Workflow

### Working with Databricks Asset Bundles

```bash
# Validate configuration
databricks bundle validate

# Deploy to Databricks
databricks bundle deploy

# Run the data ingestion pipeline
databricks bundle run ingest_kaggle_data
```

### Monitoring Jobs

```bash
# List jobs
databricks jobs list

# Get job run details
databricks runs get --run-id <run-id>
```

### Code Formatting

```bash
poetry run black src/
poetry run isort src/
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

Add `DATABRICKS_CLUSTER_ID` to your `.env` file:
```env
DATABRICKS_CLUSTER_ID=0123-456789-abc12345
```

### Connection Issues

1. Ensure your cluster is running in Databricks
2. Verify `DATABRICKS_HOST` and `DATABRICKS_TOKEN` are correct
3. Check that your token has not expired

## 🔐 Security

- Store credentials in Databricks Secrets for production
- Use `.env` for local development (never commit!)
- Keep `.databrickscfg` secure and never commit to version control

## 📝 License

See [LICENSE](LICENSE) file for details.
