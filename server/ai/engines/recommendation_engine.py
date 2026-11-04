"""
Recommendation engine for crop selection based on weather, soil, and section characteristics
FIXED VERSION — realistic + non-strict
"""

import random
from typing import Dict, List
from ai.utils.crop_database import (
    get_crops_by_season,
    normalize_soil_type,
)

# ---------------------------------------------------------
# 🌧️ Convert short-term weather → seasonal estimate
# ---------------------------------------------------------
def _estimate_seasonal_weather(weather: dict, season: str) -> dict:
    """
    WeatherAPI only gives ~14 day forecast.
    Convert it into seasonal expectation.
    """

    temp = weather.get("temperature", 27)
    rainfall = weather.get("rainfall", 50)
    humidity = weather.get("humidity", 50)

    # For kharif assume monsoon will come
    if season == "kharif":
        seasonal_rainfall = max(rainfall * 8, 600)
    elif season == "rabi":
        seasonal_rainfall = max(rainfall * 3, 120)
    else:
        seasonal_rainfall = rainfall * 2

    return {
        "temperature": temp,
        "rainfall": seasonal_rainfall,
        "humidity": humidity,
    }


# ---------------------------------------------------------
# 🌱 Soft suitability check (NOT strict)
# ---------------------------------------------------------
def is_crop_suitable_soft(crop: dict, soil_type: str, weather: dict) -> bool:
    """
    Much softer filtering.
    Only rejects crops in extreme mismatch.
    """

    soil_type = normalize_soil_type(soil_type)

    # Soil compatibility
    if soil_type not in [s.lower() for s in crop.get("soil_types", [])]:
        return False

    temp = weather.get("temperature", 25)
    rainfall = weather.get("rainfall", 500)

    # Temperature tolerance (±10°C allowed)
    if temp < crop["min_temp"] - 10 or temp > crop["max_temp"] + 10:
        return False

    # Rainfall tolerance (allow irrigation scenario)
    if rainfall < crop["min_rainfall"] * 0.3:
        return False

    return True


# ---------------------------------------------------------
# 📉 Risk calculation (improved)
# ---------------------------------------------------------
def calculate_crop_risk(crop: dict, weather: dict, water_source: str, near_water: bool) -> float:
    risk = 0.0

    # Temperature risk
    temp = weather.get("temperature", 25)
    temp_optimal = (crop["min_temp"] + crop["max_temp"]) / 2
    temp_dev = abs(temp - temp_optimal) / temp_optimal
    risk += min(temp_dev, 0.3)

    # Rainfall risk
    rainfall = weather.get("rainfall", 500)
    rain_optimal = (crop["min_rainfall"] + crop["max_rainfall"]) / 2
    rain_dev = abs(rainfall - rain_optimal) / rain_optimal
    risk += min(rain_dev * 0.5, 0.3)

    # Water source reliability
    water_source_lower = water_source.lower()

    source_risk_map = {
        "canal": 0.2,
        "borewell": 0.3,
        "well": 0.35,
        "rain": 0.5,
        "pond": 0.4,
    }

    source_risk = 0.35
    for k, v in source_risk_map.items():
        if k in water_source_lower:
            source_risk = v

    requirement_multiplier = {
        "very high": 1.5,
        "high": 1.2,
        "medium": 1.0,
        "low": 0.7,
    }

    water_req = crop.get("water_requirement", "medium")
    water_risk = source_risk * requirement_multiplier.get(water_req, 1.0)

    if near_water:
        water_risk *= 0.75

    risk += min(water_risk, 0.4)

    return round(min(risk, 1.0), 2)


# ---------------------------------------------------------
# 🌾 Diversify across sections
# ---------------------------------------------------------
def diversify_crops_across_sections(
    suitable_crops: List[dict],
    sections: List[str],
    num_crops_per_section: int = 2
) -> Dict[str, List[dict]]:

    if not suitable_crops:
        return {s: [] for s in sections}

    sorted_crops = sorted(suitable_crops, key=lambda x: x["risk"])

    result = {}
    for idx, section in enumerate(sections):
        picks = []
        start = idx % len(sorted_crops)

        for i in range(num_crops_per_section):
            crop_idx = (start + i) % len(sorted_crops)
            picks.append(sorted_crops[crop_idx])

        result[section] = picks

    return result


# ---------------------------------------------------------
# 🚜 MAIN FUNCTION
# ---------------------------------------------------------
def recommend_crops(payload: Dict, weather: Dict) -> Dict[str, List[Dict]]:
    season = payload.get("season", "kharif")
    soil_type = payload.get("soil_type", "Black Soil")
    soil_sections = payload.get("soil_sections", [])
    sections = payload.get("sections", [])

    # Convert short-term → seasonal
    effective_weather = _estimate_seasonal_weather(weather, season)

    print(f"[DEBUG] Effective seasonal weather: {effective_weather}")

    all_crops = get_crops_by_season(season)

    all_suitable = []

    for crop in all_crops:
        if is_crop_suitable_soft(crop, soil_type, effective_weather):

            # average risk (will vary per section later)
            risk = calculate_crop_risk(
                crop,
                effective_weather,
                "canal",
                True
            )

            all_suitable.append({
                "crop": crop["name"],
                "risk": risk,
                "budget": crop["base_cost_per_acre"],
                "_full": crop
            })

    # 🛟 SAFETY: if nothing suitable → still recommend top crops
    if not all_suitable:
        print("[WARNING] No suitable crops → using fallback list")
        for crop in all_crops[:4]:
            all_suitable.append({
                "crop": crop["name"],
                "risk": 0.6,
                "budget": crop["base_cost_per_acre"],
                "_full": crop
            })

    diversified = diversify_crops_across_sections(
        all_suitable,
        sections,
        num_crops_per_section=2
    )

    final = {}
    for section, crops in diversified.items():
        final[section] = [
            {
                "crop": c["crop"],
                "risk": c["risk"],
                "budget": c["budget"]
            }
            for c in crops
        ]

    return final
