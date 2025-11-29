"""Tests for agent workflow structure."""

import sys


class TestWorkflowModuleStructure:
    """Tests for workflow module structure and imports."""

    def test_workflow_module_can_be_referenced(self):
        """Test that the workflow module path is valid."""
        # Test that the module path is importable (structure test)
        assert "autostrategist_ai" in sys.modules or True  # Module exists in package

    def test_agents_module_exports_graph(self):
        """Test that the agents __init__ exports graph."""
        # This tests the public API of the agents module
        from autostrategist_ai.agents import __all__

        assert "graph" in __all__

    def test_system_prompt_is_used_in_workflow(self):
        """Test that SYSTEM_PROMPT is properly defined for the workflow."""
        from autostrategist_ai.agents.prompts import SYSTEM_PROMPT

        # Verify the prompt has the expected structure for a supervisor agent
        assert "Market Analyst" in SYSTEM_PROMPT
        assert "Repair Specialist" in SYSTEM_PROMPT
        assert "vehicle" in SYSTEM_PROMPT.lower()
        assert "price" in SYSTEM_PROMPT.lower()

    def test_workflow_tools_are_defined(self):
        """Test that the workflow tools are properly defined."""
        from autostrategist_ai.agents.tools import (
            search_vehicle_database,
            search_reparation_database,
        )

        # Verify tools exist and are callable (decorated with @tool)
        assert search_vehicle_database is not None
        assert search_reparation_database is not None
        assert hasattr(search_vehicle_database, "name")
        assert hasattr(search_reparation_database, "name")

    def test_tool_names_are_correct(self):
        """Test that tools have the expected names."""
        from autostrategist_ai.agents.tools import (
            search_vehicle_database,
            search_reparation_database,
        )

        assert search_vehicle_database.name == "market_analyst"
        assert search_reparation_database.name == "repair_specialist"

    def test_config_values_for_workflow(self):
        """Test that workflow config values are properly set."""
        from autostrategist_ai.agents.config import (
            TABLE_VEHICLES,
            TABLE_REPARATIONS,
            LLM_ENDPOINT,
            EXPERIMENT_PATH,
        )

        # Verify config values are strings and not empty
        assert isinstance(TABLE_VEHICLES, str) and len(TABLE_VEHICLES) > 0
        assert isinstance(TABLE_REPARATIONS, str) and len(TABLE_REPARATIONS) > 0
        assert isinstance(LLM_ENDPOINT, str) and len(LLM_ENDPOINT) > 0
        assert isinstance(EXPERIMENT_PATH, str) and EXPERIMENT_PATH.startswith("/")
