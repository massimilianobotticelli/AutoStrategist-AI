"""Tests for car model cleaning functions."""

import pandas as pd

# Import the pure functions that don't need Databricks
from autostrategist_ai.ingestion.car_models_clean import (
    get_model_counts,
    clean_model_names,
)


class TestGetModelCounts:
    """Tests for the get_model_counts function."""

    def test_get_model_counts_basic(self):
        """Test counting models from a simple dataframe."""
        df = pd.DataFrame({
            "manufacturer": ["toyota", "toyota", "ford", "ford", "ford"],
            "model": ["camry", "camry", "mustang", "f-150", "mustang"],
            "price": [25000, 26000, 35000, 40000, 36000],
        })
        
        result = get_model_counts(df)
        
        assert "manufacturer" in result.columns
        assert "model" in result.columns
        assert len(result) == 3  # 3 unique (manufacturer, model) pairs

    def test_get_model_counts_returns_unique_pairs(self):
        """Test that get_model_counts returns unique manufacturer-model pairs."""
        df = pd.DataFrame({
            "manufacturer": ["honda", "honda", "honda"],
            "model": ["civic", "civic", "accord"],
            "year": [2020, 2021, 2020],
        })
        
        result = get_model_counts(df)
        
        # Should have 2 unique pairs: (honda, civic) and (honda, accord)
        assert len(result) == 2


class TestCleanModelNames:
    """Tests for the clean_model_names function."""

    def test_clean_model_names_normalizes_variants(self):
        """Test that model variants are normalized to base model name."""
        df = pd.DataFrame({
            "manufacturer": ["toyota", "toyota", "toyota"],
            "model": ["Camry LE", "CAMRY XSE", "camry hybrid"],
        })
        
        result = clean_model_names(df.copy(), "toyota", "camry")
        
        # All should be normalized to "camry"
        assert all(result["model"] == "camry")

    def test_clean_model_names_only_affects_matching_manufacturer(self):
        """Test that only the specified manufacturer is affected."""
        df = pd.DataFrame({
            "manufacturer": ["toyota", "ford"],
            "model": ["camry LE", "camry look-alike"],  # ford has "camry" in name
        })
        
        result = clean_model_names(df.copy(), "toyota", "camry")
        
        # Toyota's model should be normalized
        assert result[result["manufacturer"] == "toyota"]["model"].iloc[0] == "camry"
        # Ford's model should remain unchanged
        assert result[result["manufacturer"] == "ford"]["model"].iloc[0] == "camry look-alike"

    def test_clean_model_names_case_insensitive(self):
        """Test that model matching is case insensitive."""
        df = pd.DataFrame({
            "manufacturer": ["ford", "ford", "ford"],
            "model": ["MUSTANG GT", "Mustang", "mustang convertible"],
        })
        
        result = clean_model_names(df.copy(), "ford", "mustang")
        
        assert all(result["model"] == "mustang")

    def test_clean_model_names_no_match(self):
        """Test that non-matching rows remain unchanged."""
        df = pd.DataFrame({
            "manufacturer": ["toyota", "toyota"],
            "model": ["corolla", "rav4"],
        })
        
        result = clean_model_names(df.copy(), "toyota", "camry")
        
        # Neither should change since neither contains "camry"
        assert "corolla" in result["model"].values
        assert "rav4" in result["model"].values

    def test_clean_model_names_returns_dataframe(self):
        """Test that the function returns a DataFrame."""
        df = pd.DataFrame({
            "manufacturer": ["honda"],
            "model": ["civic"],
        })
        
        result = clean_model_names(df.copy(), "honda", "civic")
        
        assert isinstance(result, pd.DataFrame)
