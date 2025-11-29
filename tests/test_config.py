"""Tests for agent configuration."""

from autostrategist_ai.agents.config import (
    TABLE_VEHICLES,
    TABLE_REPARATIONS,
    EXPERIMENT_PATH,
    LLM_ENDPOINT,
)


def test_table_vehicles_is_defined():
    """Test that TABLE_VEHICLES config is properly defined."""
    assert TABLE_VEHICLES is not None
    assert isinstance(TABLE_VEHICLES, str)
    assert len(TABLE_VEHICLES) > 0


def test_table_reparations_is_defined():
    """Test that TABLE_REPARATIONS config is properly defined."""
    assert TABLE_REPARATIONS is not None
    assert isinstance(TABLE_REPARATIONS, str)
    assert len(TABLE_REPARATIONS) > 0


def test_experiment_path_is_defined():
    """Test that EXPERIMENT_PATH config is properly defined."""
    assert EXPERIMENT_PATH is not None
    assert isinstance(EXPERIMENT_PATH, str)
    assert EXPERIMENT_PATH.startswith("/")


def test_llm_endpoint_is_defined():
    """Test that LLM_ENDPOINT config is properly defined."""
    assert LLM_ENDPOINT is not None
    assert isinstance(LLM_ENDPOINT, str)
    assert len(LLM_ENDPOINT) > 0
