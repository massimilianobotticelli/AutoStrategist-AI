"""Tests for agent tools - focusing on query building logic."""

from autostrategist_ai.agents.data_structures import VehicleData, RepairData


# Import the query building functions directly (they don't need Databricks)
# We test these since they contain the core logic without external dependencies


class TestBuildMarketQuery:
    """Tests for the build_market_query function logic."""

    def test_build_query_with_all_vehicle_fields(self):
        """Test building a market query with all vehicle fields."""
        from autostrategist_ai.agents.tools import build_market_query

        vehicle = VehicleData(
            manufacturer="Toyota",
            model="Camry",
            year=2020,
            condition="good",
            odometer=50000,
        )
        query = build_market_query(vehicle)

        # Check that key elements are in the query
        assert "Toyota" in query
        assert "Camry" in query
        assert "2019" in query  # year - 1
        assert "2021" in query  # year + 1
        assert "good" in query
        assert "30000" in query  # odometer - 20000
        assert "70000" in query  # odometer + 20000
        assert "vehicles_enriched" in query

    def test_build_query_with_minimal_fields(self):
        """Test building a market query with only manufacturer and model."""
        from autostrategist_ai.agents.tools import build_market_query

        vehicle = VehicleData(
            manufacturer="Ford",
            model="Mustang",
        )
        query = build_market_query(vehicle)

        assert "Ford" in query
        assert "Mustang" in query
        assert "ILIKE" in query
        assert "vehicles_enriched" in query

    def test_build_query_without_odometer(self):
        """Test that query without odometer doesn't include mileage filter."""
        from autostrategist_ai.agents.tools import build_market_query

        vehicle = VehicleData(
            manufacturer="Honda",
            model="Civic",
            year=2019,
        )
        query = build_market_query(vehicle)

        assert "Honda" in query
        assert "odometer BETWEEN" not in query

    def test_build_query_includes_aggregations(self):
        """Test that market query includes price aggregation functions."""
        from autostrategist_ai.agents.tools import build_market_query

        vehicle = VehicleData(manufacturer="BMW")
        query = build_market_query(vehicle)

        assert "AVG(price)" in query
        assert "PERCENTILE_APPROX" in query or "median" in query.lower()
        assert "COUNT(*)" in query


class TestBuildRepairQuery:
    """Tests for the build_repair_query function logic."""

    def test_build_repair_query_with_components(self):
        """Test building a repair query with component list."""
        from autostrategist_ai.agents.tools import build_repair_query

        repair = RepairData(
            diagnosis="squeaking noise",
            components=["brake pads", "rotors"],
        )
        query = build_repair_query(repair)

        assert "brake pads" in query.lower()
        assert "rotors" in query.lower()
        assert "reparations" in query
        assert "reparation_cost" in query

    def test_build_repair_query_with_single_component(self):
        """Test building a repair query with single component."""
        from autostrategist_ai.agents.tools import build_repair_query

        repair = RepairData(
            components=["battery"],
        )
        query = build_repair_query(repair)

        assert "battery" in query.lower()
        assert "reparations" in query

    def test_build_repair_query_with_diagnosis_only(self):
        """Test building a repair query with only diagnosis."""
        from autostrategist_ai.agents.tools import build_repair_query

        repair = RepairData(
            diagnosis="engine won't start",
        )
        query = build_repair_query(repair)

        assert "engine won't start" in query.lower()
        assert "diagnostic" in query.lower()

    def test_build_repair_query_searches_multiple_columns(self):
        """Test that repair query searches both component and diagnostic columns."""
        from autostrategist_ai.agents.tools import build_repair_query

        repair = RepairData(components=["transmission"])
        query = build_repair_query(repair)

        assert "component" in query.lower()
        assert "diagnostic" in query.lower()
