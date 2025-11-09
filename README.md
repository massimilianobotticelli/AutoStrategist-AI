# AutoStrategist-AI

An AI-powered platform for optimizing second-hand car sales, built on Databricks for the hackathon.

## 🏗️ Architecture

This project uses a modern data & AI architecture on Databricks:

- **Bronze Layer**: Raw Kaggle data ingestion
- **Silver Layer**: Cleaned and standardized data
- **Gold Layer**: Aggregated market metrics
- **AI Agent**: LangGraph-based intelligent assistant
- **Frontend**: Streamlit app via Databricks Apps

## 🚀 Getting Started

### Prerequisites

- Docker Desktop
- Visual Studio Code with Remote - Containers extension
- Databricks workspace (Free Edition works)
- Kaggle API credentials

### Development Setup

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd AutoStrategist-AI
   ```

2. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

3. **Open in Dev Container**
   - Open VS Code
   - Press `F1` and select "Dev Containers: Reopen in Container"
   - Wait for the container to build and initialize

4. **Configure Git (if needed)**
   ```bash
   git config --global user.name "Your Name"
   git config --global user.email "your.email@example.com"
   ```

5. **Install dependencies with Poetry**
   ```bash
   poetry install
   ```

6. **Configure Databricks**
   ```bash
   databricks configure --token
   ```

7. **Initialize Databricks Asset Bundle**
   ```bash
   databricks bundle init
   ```

## 📁 Project Structure

```
/root
  ├── databricks.yml          # Main DABs definition
  ├── requirements.txt        # Python dependencies
  ├── src/
  │   ├── ingestion/          # Scripts for Kaggle -> Bronze
  │   ├── transformation/     # PySpark scripts for Silver/Gold
  │   ├── agent/              # LangGraph agent definition & tools
  │   └── utils/              # Shared helpers
  └── apps/
      └── app.py              # Streamlit frontend
```

## 🛠️ Development Workflow

### Poetry Commands

```bash
# Add a new dependency
poetry add <package-name>

# Add a development dependency
poetry add --group dev <package-name>

# Update dependencies
poetry update

# Activate virtual environment
poetry shell

# Run command in Poetry environment
poetry run <command>
```

### Running Locally

```bash
# Validate DABs configuration
poetry run databricks bundle validate

# Deploy to Databricks
poetry run databricks bundle deploy

# Run Streamlit app locally
poetry run streamlit run apps/app.py
```

### Testing

```bash
# Run tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=src tests/
```

### Code Formatting

```bash
# Format code
poetry run black src/ apps/ tests/

# Lint code
poetry run pylint src/ apps/
```

## 📊 Data Pipeline

1. **Ingestion**: Kaggle Craigslist Cars+Trucks dataset → Databricks Volumes
2. **Transformation**: PySpark jobs clean and aggregate data
3. **Gold Layer**: Pre-calculated metrics for fast agent lookups

## 🤖 AI Agent

The LangGraph agent performs:
- Market value lookup from Gold tables
- Repair cost estimation from unstructured notes
- Strategic pricing recommendations
- Sales insert generation using LLM

## 🔐 Security

- Store credentials in Databricks Secrets
- Use `.env` for local development (never commit!)
- Mount `.databrickscfg` in dev container

## 📝 License

See LICENSE file for details.
