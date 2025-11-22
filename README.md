# AutoStrategist-AI

An AI-powered platform for optimizing second-hand car sales, built on Databricks for the hackathon.

## 🏗️ Architecture

This project uses a modern data & AI architecture on Databricks:

- **Bronze Layer**: Raw Kaggle data ingestion
- **Silver Layer**: Cleaned and standardized data
- **Gold Layer**: Aggregated market metrics and analytics

## 🚀 Getting Started

### Prerequisites

- Databricks workspace (Free Edition works)
- Databricks CLI installed ([installation guide](https://docs.databricks.com/dev-tools/cli/install.html))
- Kaggle API credentials (for data ingestion)

### Development Setup

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd AutoStrategist-AI
   ```

2. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials:
   # - KAGGLE_USERNAME and KAGGLE_KEY (required for data ingestion)
   # - DATABRICKS_HOST and DATABRICKS_TOKEN (for programmatic access)
   # - OPENAI_API_KEY (if using external LLM)
   ```

3. **Configure Databricks CLI**
   ```bash
   databricks configure --token
   # Enter your Databricks workspace URL and personal access token
   ```

4. **Update Databricks Asset Bundle configuration**
   ```bash
   cp databricks.example.yml databricks.yml
   # Edit databricks.yml:
   # - Update workspace.host with your Databricks workspace URL
   # - Update variables.my_cluster_id with your cluster ID
   #   (find this in your Databricks workspace under Compute -> [your cluster] -> Advanced Options)
   ```

5. **Validate and deploy the bundle**
   ```bash
   databricks bundle validate
   databricks bundle deploy
   ```

## 📁 Project Structure

```
/root
  ├── databricks.yml          # Main DABs definition (user-configured)
  ├── databricks.example.yml  # Example DABs configuration template
  ├── .env.example            # Example environment variables template
  ├── resources/
  │   └── ingestion.yml       # Job definitions for DABs (defines ingest_kaggle_data job)
  └── src/
      └── ingestion/          # Databricks notebooks for data pipeline
          ├── 00_load_data.ipynb       # Download from Kaggle
          ├── 01_ingest_data.ipynb     # Ingest to Bronze layer
          ├── 02_prepare_data.ipynb    # Transform to Silver layer
          └── 03_enrich_data.ipynb     # Enrich to Gold layer
```

## 🛠️ Development Workflow

### Working with Databricks Asset Bundles

```bash
# Validate DABs configuration
databricks bundle validate

# Deploy to Databricks (creates/updates jobs and notebooks)
databricks bundle deploy

# Run a specific job
databricks bundle run ingest_kaggle_data
```

### Editing Notebooks

You can edit the notebooks in two ways:

1. **In Databricks Workspace**: After deploying, navigate to your Databricks workspace and edit notebooks directly in the UI

2. **Locally with VS Code**: Use the Databricks extension for VS Code to sync and edit notebooks locally, then deploy changes

### Monitoring Jobs

```bash
# List jobs in your bundle
databricks jobs list

# Get job run details
databricks runs get --run-id <run-id>

# View job logs
databricks runs get-output --run-id <run-id>
```

## 📊 Data Pipeline

The data pipeline is implemented as a series of Databricks notebooks that run as jobs:

1. **00_load_data.ipynb**: Downloads the Kaggle Craigslist Cars+Trucks dataset
2. **01_ingest_data.ipynb**: Ingests raw data to Bronze layer in Databricks
3. **02_prepare_data.ipynb**: Cleans and transforms data to Silver layer using PySpark
4. **03_enrich_data.ipynb**: Enriches and aggregates data to Gold layer for analytics

The pipeline follows the medallion architecture (Bronze → Silver → Gold) and is orchestrated through Databricks Asset Bundles.

## 🔐 Security

- Store credentials in Databricks Secrets for production use
- Use `.env` for local development (never commit!)
- Keep your `.databrickscfg` file secure and never commit it to version control

## 📝 License

See LICENSE file for details.
