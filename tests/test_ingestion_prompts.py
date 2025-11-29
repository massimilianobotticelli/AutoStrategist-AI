"""Tests for ingestion prompts."""

from autostrategist_ai.ingestion.prompts import (
    PROMPT_CLEAN_MODEL,
    PROMPT_ENRICH_COLUMNS,
)


class TestIngestionPrompts:
    """Tests for ingestion prompt templates."""

    def test_clean_model_prompt_exists(self):
        """Test that PROMPT_CLEAN_MODEL is defined and has content."""
        assert PROMPT_CLEAN_MODEL is not None
        assert len(PROMPT_CLEAN_MODEL) > 100

    def test_clean_model_prompt_has_input_variable(self):
        """Test that clean model prompt has the expected input placeholder."""
        assert "{list_cars}" in PROMPT_CLEAN_MODEL

    def test_clean_model_prompt_mentions_json(self):
        """Test that clean model prompt asks for JSON output."""
        assert "json" in PROMPT_CLEAN_MODEL.lower()

    def test_clean_model_prompt_has_example(self):
        """Test that clean model prompt includes examples."""
        assert "toyota" in PROMPT_CLEAN_MODEL.lower()
        assert "corolla" in PROMPT_CLEAN_MODEL.lower()

    def test_enrich_columns_prompt_exists(self):
        """Test that PROMPT_ENRICH_COLUMNS is defined and has content."""
        assert PROMPT_ENRICH_COLUMNS is not None
        assert len(PROMPT_ENRICH_COLUMNS) > 100

    def test_enrich_columns_prompt_has_input_variable(self):
        """Test that enrich columns prompt has the expected input placeholder."""
        assert "{free_text}" in PROMPT_ENRICH_COLUMNS

    def test_enrich_columns_prompt_mentions_json(self):
        """Test that enrich columns prompt asks for JSON output."""
        assert "json" in PROMPT_ENRICH_COLUMNS.lower()

    def test_enrich_columns_prompt_handles_nulls(self):
        """Test that enrich columns prompt mentions handling missing fields as null."""
        assert "null" in PROMPT_ENRICH_COLUMNS.lower()
