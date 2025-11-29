"""Tests for agent prompts."""

from autostrategist_ai.agents.prompts import (
    SYSTEM_PROMPT,
    MARKET_ANALYST_DESCRIPTION,
    MARKET_ANALYST_SYSTEM_PROMPT,
    REPAIR_SPECIALIST_DESCRIPTION,
    REPAIR_SPECIALIST_SYSTEM_PROMPT,
)


class TestPrompts:
    """Tests for prompt definitions."""

    def test_system_prompt_exists_and_not_empty(self):
        """Test that SYSTEM_PROMPT is defined and has content."""
        assert SYSTEM_PROMPT is not None
        assert len(SYSTEM_PROMPT) > 100  # Should be substantial

    def test_system_prompt_mentions_key_concepts(self):
        """Test that SYSTEM_PROMPT contains key concepts."""
        assert "Market Analyst" in SYSTEM_PROMPT
        assert "Repair Specialist" in SYSTEM_PROMPT
        assert "vehicle" in SYSTEM_PROMPT.lower()

    def test_market_analyst_description_exists(self):
        """Test that MARKET_ANALYST_DESCRIPTION is defined."""
        assert MARKET_ANALYST_DESCRIPTION is not None
        assert len(MARKET_ANALYST_DESCRIPTION) > 0
        assert "market" in MARKET_ANALYST_DESCRIPTION.lower()

    def test_market_analyst_system_prompt_exists(self):
        """Test that MARKET_ANALYST_SYSTEM_PROMPT is defined."""
        assert MARKET_ANALYST_SYSTEM_PROMPT is not None
        assert len(MARKET_ANALYST_SYSTEM_PROMPT) > 0

    def test_repair_specialist_description_exists(self):
        """Test that REPAIR_SPECIALIST_DESCRIPTION is defined."""
        assert REPAIR_SPECIALIST_DESCRIPTION is not None
        assert len(REPAIR_SPECIALIST_DESCRIPTION) > 0
        assert "repair" in REPAIR_SPECIALIST_DESCRIPTION.lower()

    def test_repair_specialist_system_prompt_exists(self):
        """Test that REPAIR_SPECIALIST_SYSTEM_PROMPT is defined."""
        assert REPAIR_SPECIALIST_SYSTEM_PROMPT is not None
        assert len(REPAIR_SPECIALIST_SYSTEM_PROMPT) > 0
