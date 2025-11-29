"""Data structures for the AutoStrategist AI agent system.

This module defines Pydantic models used for structured data validation
and serialization throughout the agent workflow, including vehicle information,
market analysis results, and repair estimates.
"""

from typing import List, Optional

from pydantic import BaseModel, field_validator


class VehicleData(BaseModel):
    """Vehicle information model for market and repair analysis.

    Attributes:
        year: Manufacturing year of the vehicle.
        manufacturer: Brand/manufacturer name (e.g., 'Toyota', 'Ford').
        model: Specific model name (e.g., 'Camry', 'F-150').
        condition: Current condition of the vehicle (e.g., 'excellent', 'good', 'fair').
        cylinders: Number of engine cylinders.
        fuel: Fuel type (e.g., 'gas', 'diesel', 'electric', 'hybrid').
        odometer: Current mileage reading in miles.
        transmission: Transmission type (e.g., 'automatic', 'manual').
        drive: Drive type (e.g., 'fwd', 'rwd', '4wd').
        car_type: Vehicle body type (e.g., 'sedan', 'SUV', 'truck').
        paint_color: Exterior color of the vehicle.
    """

    year: Optional[int] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    condition: Optional[str] = None
    cylinders: Optional[int] = None
    fuel: Optional[str] = None
    odometer: Optional[int] = None
    transmission: Optional[str] = None
    drive: Optional[str] = None
    car_type: Optional[str] = None
    paint_color: Optional[str] = None


class MarketAnalysisResults(BaseModel):
    """Results from vehicle market price analysis.

    Attributes:
        average_price: Mean selling price of comparable vehicles.
        median_price: Median selling price of comparable vehicles.
        price_std_dev: Standard deviation of prices, indicating market variability.
        num_cars_sold: Number of comparable vehicles found in the analysis.
    """

    average_price: Optional[float] = None
    median_price: Optional[float] = None
    price_std_dev: Optional[float] = None
    num_cars_sold: Optional[int] = None


class RepairData(BaseModel):
    """Input data for repair cost estimation.

    Attributes:
        diagnosis: Description of the vehicle's issues or symptoms.
        components: List of specific components that need repair or inspection.
    """

    diagnosis: Optional[str] = None
    components: Optional[List[str]] = None

    @field_validator("components", mode="before")
    def convert_string_to_list(self, v):
        """Convert a single string component to a list.

        Args:
            v: Input value, either a string or list of strings.

        Returns:
            List of component strings.
        """
        if isinstance(v, str):
            return [v]
        return v


class RepairAnalysisResults(BaseModel):
    """Results from repair cost analysis.

    Attributes:
        total_estimated_cost: Total estimated cost for all identified repairs.
        identified_repairs: Dictionary mapping repair items to their individual costs.
    """

    total_estimated_cost: Optional[float] = None
    identified_repairs: Optional[dict] = None
