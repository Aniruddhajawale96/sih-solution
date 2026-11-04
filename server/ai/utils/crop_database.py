"""
Crop database containing information about various crops
"""

# Comprehensive crop database
CROP_DATABASE = {
    # KHARIF CROPS (Monsoon crops: June-October)
    "kharif": [
        {
            "name": "rice",
            "min_temp": 20,
            "max_temp": 37,
            "min_rainfall": 1000,
            "max_rainfall": 2500,
            "soil_types": ["clay", "loamy", "black soil"],
            "water_requirement": "high",
            "base_cost_per_acre": 15000,
            "base_yield_per_acre": 25,  # quintals
            "market_price_per_quintal": 2000,
            "growth_period_days": 120,
        },
        {
            "name": "maize",
            "min_temp": 18,
            "max_temp": 35,
            "min_rainfall": 500,
            "max_rainfall": 1200,
            "soil_types": ["loamy", "sandy", "black soil", "red soil"],
            "water_requirement": "medium",
            "base_cost_per_acre": 10000,
            "base_yield_per_acre": 30,
            "market_price_per_quintal": 1800,
            "growth_period_days": 90,
        },
        {
            "name": "cotton",
            "min_temp": 21,
            "max_temp": 35,
            "min_rainfall": 500,
            "max_rainfall": 1000,
            "soil_types": ["black soil", "loamy", "alluvial"],
            "water_requirement": "medium",
            "base_cost_per_acre": 18000,
            "base_yield_per_acre": 15,
            "market_price_per_quintal": 6000,
            "growth_period_days": 150,
        },
        {
            "name": "soybean",
            "min_temp": 20,
            "max_temp": 32,
            "min_rainfall": 600,
            "max_rainfall": 1000,
            "soil_types": ["black soil", "loamy", "red soil"],
            "water_requirement": "medium",
            "base_cost_per_acre": 12000,
            "base_yield_per_acre": 12,
            "market_price_per_quintal": 4500,
            "growth_period_days": 100,
        },
        {
            "name": "bajra",
            "min_temp": 25,
            "max_temp": 35,
            "min_rainfall": 400,
            "max_rainfall": 800,
            "soil_types": ["sandy", "loamy", "black soil"],
            "water_requirement": "low",
            "base_cost_per_acre": 8000,
            "base_yield_per_acre": 18,
            "market_price_per_quintal": 2200,
            "growth_period_days": 75,
        },
        {
            "name": "groundnut",
            "min_temp": 20,
            "max_temp": 30,
            "min_rainfall": 500,
            "max_rainfall": 1250,
            "soil_types": ["sandy", "loamy", "red soil", "black soil"],
            "water_requirement": "medium",
            "base_cost_per_acre": 14000,
            "base_yield_per_acre": 20,
            "market_price_per_quintal": 5500,
            "growth_period_days": 110,
        },
    ],
    
    # RABI CROPS (Winter crops: October-March)
    "rabi": [
        {
            "name": "wheat",
            "min_temp": 10,
            "max_temp": 25,
            "min_rainfall": 300,
            "max_rainfall": 1000,
            "soil_types": ["loamy", "clay", "alluvial"],
            "water_requirement": "medium",
            "base_cost_per_acre": 12000,
            "base_yield_per_acre": 28,
            "market_price_per_quintal": 2200,
            "growth_period_days": 120,
        },
        {
            "name": "mustard",
            "min_temp": 10,
            "max_temp": 25,
            "min_rainfall": 250,
            "max_rainfall": 600,
            "soil_types": ["loamy", "sandy", "clay"],
            "water_requirement": "low",
            "base_cost_per_acre": 8000,
            "base_yield_per_acre": 12,
            "market_price_per_quintal": 5000,
            "growth_period_days": 90,
        },
        {
            "name": "chickpea",
            "min_temp": 15,
            "max_temp": 30,
            "min_rainfall": 400,
            "max_rainfall": 800,
            "soil_types": ["black soil", "loamy", "clay"],
            "water_requirement": "low",
            "base_cost_per_acre": 10000,
            "base_yield_per_acre": 15,
            "market_price_per_quintal": 5500,
            "growth_period_days": 100,
        },
        {
            "name": "barley",
            "min_temp": 12,
            "max_temp": 25,
            "min_rainfall": 300,
            "max_rainfall": 700,
            "soil_types": ["loamy", "sandy", "clay"],
            "water_requirement": "low",
            "base_cost_per_acre": 9000,
            "base_yield_per_acre": 25,
            "market_price_per_quintal": 1800,
            "growth_period_days": 100,
        },
        {
            "name": "potato",
            "min_temp": 15,
            "max_temp": 25,
            "min_rainfall": 500,
            "max_rainfall": 1000,
            "soil_types": ["loamy", "sandy", "alluvial"],
            "water_requirement": "high",
            "base_cost_per_acre": 25000,
            "base_yield_per_acre": 200,
            "market_price_per_quintal": 1500,
            "growth_period_days": 90,
        },
        {
            "name": "onion",
            "min_temp": 13,
            "max_temp": 24,
            "min_rainfall": 400,
            "max_rainfall": 800,
            "soil_types": ["loamy", "sandy", "alluvial"],
            "water_requirement": "medium",
            "base_cost_per_acre": 20000,
            "base_yield_per_acre": 150,
            "market_price_per_quintal": 2000,
            "growth_period_days": 120,
        },
    ],
    
    # ALL YEAR / ZAID CROPS (Summer crops or year-round)
    "all year": [
        {
            "name": "sugarcane",
            "min_temp": 20,
            "max_temp": 35,
            "min_rainfall": 1000,
            "max_rainfall": 2500,
            "soil_types": ["loamy", "clay", "black soil"],
            "water_requirement": "very high",
            "base_cost_per_acre": 35000,
            "base_yield_per_acre": 400,
            "market_price_per_quintal": 350,
            "growth_period_days": 365,
        },
        {
            "name": "turmeric",
            "min_temp": 20,
            "max_temp": 35,
            "min_rainfall": 1500,
            "max_rainfall": 2250,
            "soil_types": ["loamy", "clay", "red soil"],
            "water_requirement": "high",
            "base_cost_per_acre": 30000,
            "base_yield_per_acre": 50,
            "market_price_per_quintal": 8000,
            "growth_period_days": 270,
        },
        {
            "name": "banana",
            "min_temp": 15,
            "max_temp": 35,
            "min_rainfall": 1200,
            "max_rainfall": 2700,
            "soil_types": ["loamy", "clay", "alluvial"],
            "water_requirement": "very high",
            "base_cost_per_acre": 40000,
            "base_yield_per_acre": 250,
            "market_price_per_quintal": 1500,
            "growth_period_days": 365,
        },
        {
            "name": "papaya",
            "min_temp": 20,
            "max_temp": 35,
            "min_rainfall": 1000,
            "max_rainfall": 2000,
            "soil_types": ["loamy", "sandy", "alluvial"],
            "water_requirement": "high",
            "base_cost_per_acre": 28000,
            "base_yield_per_acre": 180,
            "market_price_per_quintal": 1200,
            "growth_period_days": 300,
        },
        {
            "name": "cucumber",
            "min_temp": 18,
            "max_temp": 35,
            "min_rainfall": 400,
            "max_rainfall": 800,
            "soil_types": ["loamy", "sandy"],
            "water_requirement": "medium",
            "base_cost_per_acre": 15000,
            "base_yield_per_acre": 100,
            "market_price_per_quintal": 1000,
            "growth_period_days": 60,
        },
        {
            "name": "tomato",
            "min_temp": 18,
            "max_temp": 27,
            "min_rainfall": 600,
            "max_rainfall": 1500,
            "soil_types": ["loamy", "sandy", "red soil"],
            "water_requirement": "medium",
            "base_cost_per_acre": 22000,
            "base_yield_per_acre": 120,
            "market_price_per_quintal": 1800,
            "growth_period_days": 90,
        },
    ],
}


def get_crops_by_season(season: str):
    """Get list of crops for a specific season"""
    season_lower = season.lower()
    return CROP_DATABASE.get(season_lower, [])


def normalize_soil_type(soil_type: str) -> str:
    """Normalize soil type string for matching"""
    return soil_type.lower().strip()


def is_crop_suitable(crop: dict, soil_type: str, weather: dict) -> bool:
    """
    Check if a crop is suitable based on soil and weather conditions
    """
    normalized_soil = normalize_soil_type(soil_type)
    
    # Check soil compatibility
    soil_match = any(
        normalized_soil in normalize_soil_type(s) or normalize_soil_type(s) in normalized_soil
        for s in crop["soil_types"]
    )
    
    if not soil_match:
        return False
    
    # Check temperature range
    temp = weather.get("temperature", 25)
    if not (crop["min_temp"] <= temp <= crop["max_temp"]):
        return False
    
    # Check rainfall range (more lenient)
    rainfall = weather.get("rainfall", 500)
    # Allow some flexibility in rainfall requirements
    rainfall_tolerance = 0.3  # 30% tolerance
    min_rain_adjusted = crop["min_rainfall"] * (1 - rainfall_tolerance)
    max_rain_adjusted = crop["max_rainfall"] * (1 + rainfall_tolerance)
    
    if not (min_rain_adjusted <= rainfall <= max_rain_adjusted):
        return False
    
    return True