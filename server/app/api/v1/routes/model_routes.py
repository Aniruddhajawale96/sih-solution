from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any
from ai.main import run_ai_with_profit

router = APIRouter()


# Pydantic models for request validation
class Location(BaseModel):
    latitude: float = Field(..., ge=-90, le=90, description="Latitude coordinate")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude coordinate")


class SoilSection(BaseModel):
    section_name: str = Field(..., description="Name/ID of the soil section")
    water_source: str = Field(..., description="Water source type (e.g., Canal, Borewell)")
    near_water: bool = Field(..., description="Whether section is near water")


class FarmInput(BaseModel):
    location: Location
    soil_type: str = Field(..., description="Type of soil (e.g., black soil, red soil)")
    soil_sections: List[SoilSection] = Field(..., min_length=1, description="List of soil sections")
    budget: float = Field(..., gt=0, description="Available budget")
    crop_type: str = Field(..., description="Crop type/season (e.g., kharif, rabi)")

    class Config:
        json_schema_extra = {
            "example": {
                "location": {"latitude": 20.0, "longitude": 77.0},
                "soil_type": "black soil",
                "soil_sections": [
                    {"section_name": "A", "water_source": "Canal", "near_water": True},
                    {"section_name": "B", "water_source": "Borewell", "near_water": True},
                    {"section_name": "C", "water_source": "Canal", "near_water": True}
                ],
                "budget": 100000,
                "crop_type": "kharif"
            }
        }


# Response models
class CropRecommendation(BaseModel):
    crop: str
    risk: float
    budget: float


class CropProfit(BaseModel):
    crop: str
    expected_profit: float
    risk: float
    cost: float


class RecommendationResponse(BaseModel):
    status: str
    recommendations: Dict[str, List[Dict[str, Any]]]
    expected_profit: Dict[str, List[Dict[str, Any]]]


@router.get("/status")
def model_status():
    """Check if the model service is working"""
    return {"status": "working..."}


@router.post(
    "/getRecommendation",
    response_model=RecommendationResponse
)
def get_recommendation(
    payload: FarmInput,
):
    """
    Get crop recommendations for a farm based on soil sections and weather data.

    Uses the AI main module which:
    - Fetches weather data automatically
    - Generates crop recommendations
    - Calculates expected profit

    Returns the top recommendations for each soil section with:
    - Risk assessment
    - Expected profit
    - Budget requirements
    """
    try:
        farm_dict = payload.model_dump()
        result = run_ai_with_profit(farm_dict)

        if "recommendations" not in result or "expected_profit" not in result:
            raise ValueError("Invalid response structure from AI module")

        return {
            "status": "success",
            "recommendations": result["recommendations"],
            "expected_profit": result["expected_profit"]
        }

    except ValueError as ve:
        raise HTTPException(status_code=400, detail=f"Validation error: {str(ve)}")
    except FileNotFoundError as fe:
        raise HTTPException(status_code=500, detail=f"Model files not found: {str(fe)}")
    except KeyError as ke:
        raise HTTPException(status_code=400, detail=f"Missing required field: {str(ke)}")
    except ImportError as ie:
        raise HTTPException(status_code=500, detail=f"AI module import error: {str(ie)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating recommendations: {str(e)}")
