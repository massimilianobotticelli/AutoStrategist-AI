"""Tests for agent data structures."""

from autostrategist_ai.agents.data_structures import (
    VehicleData,
    MarketAnalysisResults,
    RepairData,
    RepairAnalysisResults,
)


class TestVehicleData:
    """Tests for VehicleData model."""

    def test_create_vehicle_data_with_all_fields(self):
        """Test creating VehicleData with all fields populated."""
        vehicle = VehicleData(
            year=2020,
            manufacturer="Toyota",
            model="Camry",
            condition="excellent",
            cylinders=4,
            fuel="gas",
            odometer=50000,
            transmission="automatic",
            drive="fwd",
            car_type="sedan",
            paint_color="white",
        )
        assert vehicle.year == 2020
        assert vehicle.manufacturer == "Toyota"
        assert vehicle.model == "Camry"
        assert vehicle.condition == "excellent"
        assert vehicle.odometer == 50000

    def test_create_vehicle_data_with_minimal_fields(self):
        """Test creating VehicleData with only some fields."""
        vehicle = VehicleData(
            manufacturer="Ford",
            model="Mustang",
            year=2019,
        )
        assert vehicle.manufacturer == "Ford"
        assert vehicle.model == "Mustang"
        assert vehicle.year == 2019
        assert vehicle.condition is None
        assert vehicle.odometer is None

    def test_create_empty_vehicle_data(self):
        """Test creating VehicleData with no fields (all optional)."""
        vehicle = VehicleData()
        assert vehicle.year is None
        assert vehicle.manufacturer is None
        assert vehicle.model is None


class TestMarketAnalysisResults:
    """Tests for MarketAnalysisResults model."""

    def test_create_market_analysis_results(self):
        """Test creating MarketAnalysisResults with typical data."""
        results = MarketAnalysisResults(
            average_price=25000.50,
            median_price=24500.00,
            price_std_dev=3500.25,
            num_cars_sold=42,
        )
        assert results.average_price == 25000.50
        assert results.median_price == 24500.00
        assert results.price_std_dev == 3500.25
        assert results.num_cars_sold == 42

    def test_create_empty_market_analysis_results(self):
        """Test creating MarketAnalysisResults with no data."""
        results = MarketAnalysisResults()
        assert results.average_price is None
        assert results.num_cars_sold is None


class TestRepairData:
    """Tests for RepairData model."""

    def test_create_repair_data_with_list(self):
        """Test creating RepairData with a list of components."""
        repair = RepairData(
            diagnosis="squeaking noise when braking",
            components=["brake pads", "rotors"],
        )
        assert repair.diagnosis == "squeaking noise when braking"
        assert repair.components == ["brake pads", "rotors"]
        assert len(repair.components) == 2

    def test_create_repair_data_with_single_string_component(self):
        """Test that a single string component is converted to a list."""
        repair = RepairData(
            diagnosis="car won't start",
            components="battery",
        )
        assert repair.components == ["battery"]

    def test_create_empty_repair_data(self):
        """Test creating RepairData with no data."""
        repair = RepairData()
        assert repair.diagnosis is None
        assert repair.components is None


class TestRepairAnalysisResults:
    """Tests for RepairAnalysisResults model."""

    def test_create_repair_analysis_results(self):
        """Test creating RepairAnalysisResults with typical data."""
        results = RepairAnalysisResults(
            total_estimated_cost=450.00,
            identified_repairs={
                "brake pads": 150.00,
                "rotors": 300.00,
            },
        )
        assert results.total_estimated_cost == 450.00
        assert results.identified_repairs["brake pads"] == 150.00
        assert len(results.identified_repairs) == 2

    def test_create_empty_repair_analysis_results(self):
        """Test creating RepairAnalysisResults with no data."""
        results = RepairAnalysisResults()
        assert results.total_estimated_cost is None
        assert results.identified_repairs is None
