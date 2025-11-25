from typing import List, Optional

from pydantic import BaseModel, field_validator


class VehicleData(BaseModel):
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
    average_price: Optional[float] = None
    median_price: Optional[float] = None
    price_std_dev: Optional[float] = None
    num_cars_sold: Optional[int] = None


class RepairData(BaseModel):
    diagnosis: Optional[str] = None
    components: Optional[List[str]] = None

    @field_validator("components", mode="before")
    def convert_string_to_list(cls, v):
        # If the LLM sends a string, wrap it in a list
        if isinstance(v, str):
            return [v]
        return v


class RepairAnalysisResults(BaseModel):
    total_estimated_cost: Optional[float] = None
    identified_repairs: Optional[dict] = None
