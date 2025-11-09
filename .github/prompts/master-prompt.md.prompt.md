---
mode: agent
---

### Master Prompt for GitHub Copilot

**Subject:** Databricks Hackathon Project - "AI Car Sales Consultant" Platform Specification

You are an expert AI Software Engineer assisting me in building a production-grade Data & AI platform on Databricks for a hackathon. We are using a "Pro-Code" approach, leveraging standard software engineering practices rather than just notebooks.

Please internalize the following Technical Stack, Architecture, and Functional Requirements to assist me in implementing this solution.

#### 1\. Technical Stack & Constraints

  * **Platform:** Databricks (Free Edition, utilizing Model Serving and Databricks Apps for demonstration purposes).
  * **Development Environment:** Visual Studio Code (local) using **Databricks Connect** for remote execution.
  * **Deployment & Infrastructure:** **Databricks Asset Bundles (DABs)** for defining all resources (jobs, pipelines, experiment, app, model serving).
  * **Data Engineering:** Python (PySpark) managed via DABs Jobs/Pipelines.
  * **AI/ML:**
      * **MLflow** for experiment tracking and model logging.
      * **LangGraph** for building the stateful AI Agent.
      * **Databricks Model Serving** to expose the agent as a REST API.
  * **UI:** **Databricks Apps** (likely Streamlit) as the frontend.

#### 2\. High-Level Architecture

The system helps users sell their second-hand cars by analyzing market data and drafting optimized sales inserts.

  * **Bronze Layer:** Raw data ingested from Kaggle (Craigslist Cars+Trucks dataset) into Databricks Volumes.
  * **Silver Layer:** Cleaned Delta tables (parsed dates, standardized make/model, separated unstructured descriptions).
  * **Gold Layer:** Aggregated market metrics (depreciation curves, average price per trim level) used by the Agent for lookups.
  * **AI Agent:** A LangGraph agent that takes user car details + unstructured notes, queries Gold data for valuation, estimates repair costs from a lookup table, and uses an LLM to draft the final sales text.
  * **Frontend:** A web app where users input their car info and receive the agent's assessment and drafted text.

#### 3\. Detailed Module Requirements

**A. Project Structure (DABs standard)**
Maintain a clean structure separating standard Python code from Databricks specific definitions:

```
/root
  ├── databricks.yml          # Main DABs definition
  ├── requirements.txt        # Python dependencies
  ├── src/
  │   ├── ingestion/          # Scripts for Kaggle -> Bronze
  │   ├── transformation/     # PySpark scripts for Silver/Gold
  │   ├── agent/              # LangGraph agent definition & tools
  │   └── utils/              # Shared helpers (e.g., Spark session getter)
  └── apps/
      └── app.py              # Streamlit frontend entry point
```

**B. Data Ingestion (Bronze)**

  * Create a Python script that uses the `kaggle` API.
  * It must authenticate using Databricks Secrets (do not hardcode credentials).
  * Download the "craigslist-carstrucks-data" dataset directly to a Databricks Volume (e.g., `/Volumes/main/default/raw_data/`).

**C. Transformation (Silver/Gold)**

  * Use PySpark via Databricks Connect.
  * **Silver:** Clean the raw CSV. Handle missing values in critical columns (price, year, odemeter). Filter for a subset of popular brands (Ford, Toyota, Honda, BMW) to keep data manageable.
  * **Gold:** Pre-calculate key metrics to speed up Agent lookups:
      * `avg_price_by_model_year`
      * `price_std_dev` (to help the agent understand price ranges).

**D. AI Agent (The Core Differentiator)**

  * Implement using `langgraph`.
  * **State:** Should track `user_input`, `market_data`, `repair_estimates`, and `final_draft`.
  * **Tools:**
    1.  `lookup_market_value(make, model, year, mileage)`: Queries Gold Delta tables.
    2.  `estimate_repairs(unstructured_notes)`: Uses an LLM to extract defects from notes (e.g., "bad brakes") and looks up costs in a static reference CSV.
  * **Node Flow:** `Input -> Market Research -> Repair Estimation -> Strategy Generation (LLM) -> Draft Writing (LLM) -> Output`.
  * Must be loggable as an MLflow PyFunc model for deployment.

**E. Databricks App (Frontend)**

  * A simple Streamlit interface.
  * Form inputs: Year, Make, Model, Mileage, Condition Notes (text area).
  * Action: "Analyze My Car" button calls the Model Serving endpoint.
  * Display: The Agent's strategic advice (e.g., "List for $15k, but mention standard alternator issues to build trust") and the ready-to-copy sales insert.