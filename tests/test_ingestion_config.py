"""Tests for ingestion configuration."""

from autostrategist_ai.ingestion.config import (
    LLM_ENDPOINT,
    CATALOG,
    SCHEMA,
    VOLUME,
    VEHICLE_TABLE,
    REPAIR_TABLE,
    VEHICLE_CSV_NAME,
    REPAIR_CSV_NAME,
    PREP_SOURCE_TABLE,
    PREP_TARGET_TABLE,
    TARGET_MANUFACTURERS,
    COLUMNS_TO_DROP,
    SAMPLE_FRACTION,
    CL_SOURCE_TABLE,
    CL_TARGET_TABLE,
    EN_SOURCE_TABLE,
    EN_TARGET_TABLE,
)


class TestIngestionConfig:
    """Tests for ingestion configuration values."""

    def test_catalog_schema_volume_defined(self):
        """Test that catalog, schema, and volume are properly defined."""
        assert CATALOG == "workspace"
        assert SCHEMA == "car_sales"
        assert isinstance(VOLUME, str) and len(VOLUME) > 0

    def test_table_names_use_catalog_schema(self):
        """Test that table names are properly constructed with catalog.schema prefix."""
        prefix = f"{CATALOG}.{SCHEMA}."
        assert VEHICLE_TABLE.startswith(prefix)
        assert REPAIR_TABLE.startswith(prefix)
        assert PREP_SOURCE_TABLE.startswith(prefix)
        assert PREP_TARGET_TABLE.startswith(prefix)

    def test_csv_names_have_extension(self):
        """Test that CSV file names have .csv extension."""
        assert VEHICLE_CSV_NAME.endswith(".csv")
        assert REPAIR_CSV_NAME.endswith(".csv")

    def test_target_manufacturers_list(self):
        """Test that target manufacturers is a non-empty list of strings."""
        assert isinstance(TARGET_MANUFACTURERS, list)
        assert len(TARGET_MANUFACTURERS) > 0
        assert all(isinstance(m, str) for m in TARGET_MANUFACTURERS)
        # Check some expected manufacturers
        assert "ford" in TARGET_MANUFACTURERS
        assert "toyota" in TARGET_MANUFACTURERS

    def test_columns_to_drop_is_list(self):
        """Test that columns to drop is a list of column names."""
        assert isinstance(COLUMNS_TO_DROP, list)
        assert len(COLUMNS_TO_DROP) > 0
        # These columns should be dropped as they're not useful for analysis
        assert "url" in COLUMNS_TO_DROP
        assert "VIN" in COLUMNS_TO_DROP

    def test_sample_fraction_is_valid(self):
        """Test that sample fraction is between 0 and 1."""
        assert isinstance(SAMPLE_FRACTION, float)
        assert 0 < SAMPLE_FRACTION <= 1

    def test_llm_endpoint_defined(self):
        """Test that LLM endpoint is properly defined."""
        assert isinstance(LLM_ENDPOINT, str)
        assert len(LLM_ENDPOINT) > 0

    def test_pipeline_table_chain(self):
        """Test that pipeline tables form a logical chain."""
        # The pipeline flows: vehicles -> vehicles_cleaned -> vehicles_models_cleaned -> vehicles_enriched
        assert "vehicles" in PREP_SOURCE_TABLE
        assert "cleaned" in PREP_TARGET_TABLE
        assert PREP_TARGET_TABLE == CL_SOURCE_TABLE  # Output of prep is input of clean
        assert "models_cleaned" in CL_TARGET_TABLE
        assert CL_TARGET_TABLE == EN_SOURCE_TABLE  # Output of clean is input of enrich
        assert "enriched" in EN_TARGET_TABLE
