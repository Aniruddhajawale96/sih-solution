from typing import Dict, Any
from ai.utils.crop_database import CROP_DATABASE

def find_crop(crop_name: str):
    for season in CROP_DATABASE.values():
        for c in season:
            if c["name"] == crop_name.lower():
                return c
    return None

def region_score(location: Dict[str, float]) -> float:
    lat = location["latitude"]

    # Simple India farming belt heuristic
    if 18 <= lat <= 28:
        rainfall = 0.7
        temp = 0.7
    else:
        rainfall = 0.5
        temp = 0.5

    return (rainfall + temp) / 2

def weather_score(location: Dict[str, float]) -> float:
    drought = 0.4
    flood = 0.3
    extreme = 0.4

    harshness = (drought + flood + extreme) / 3
    return 1 - harshness

def soil_score(soil_type: str, crop: dict, near_water: bool) -> float:

    soil_match = 1 if soil_type.lower() in crop["soil_types"] else 0.4

    water_map = {
        "low": 0.8,
        "medium": 0.7,
        "high": 0.6,
        "very high": 0.5,
    }

    water_need = water_map.get(crop["water_requirement"], 0.6)

    water_bonus = 0.1 if near_water else -0.1

    score = (soil_match + water_need) / 2 + water_bonus
    return max(0, min(score, 1))

def crop_score(crop: dict):

    temp_range = crop["max_temp"] - crop["min_temp"]
    rain_range = crop["max_rainfall"] - crop["min_rainfall"]

    temp_score = min(temp_range / 20, 1)
    rain_score = min(rain_range / 1500, 1)

    duration_penalty = min(crop["growth_period_days"] / 365, 1)

    robustness = (temp_score + rain_score + (1 - duration_penalty)) / 3
    return robustness

def final_risk(r, w, s, c):
    stability = (r + w + s + c) / 4
    risk = 1 - stability
    return round(max(0, min(risk, 1)), 2)

def recalculate_risk(payload: Dict[str, Any], ml_output: Dict[str, Any]):
    r = region_score(payload["location"])
    w = weather_score(payload["location"])
    soil_type = payload["soil_type"]

    for section in payload["soil_sections"]:
        sec_name = section["section_name"]
        near_water = section["near_water"]

        for item in ml_output["recommendations"][sec_name]:
            crop_name = item["crop"]
            crop = find_crop(crop_name)
            if not crop:
                continue

            s = soil_score(soil_type, crop, near_water)
            c = crop_score(crop)

            item["risk"] = final_risk(r, w, s, c)

        for item in ml_output["expected_profit"][sec_name]:
            crop_name = item["crop"]
            crop = find_crop(crop_name)
            if not crop:
                continue

            s = soil_score(soil_type, crop, near_water)
            c = crop_score(crop)

            item["risk"] = final_risk(r, w, s, c)

    return ml_output


if __name__ == "__main__":

    payload = {
        "location": {"latitude": 20.0, "longitude": 77.0},  # Nashik coordinates
        "soil_type": "black soil",
        "soil_sections": [
            {
                "section_name": "A",
                "water_source": "Canal",
                "near_water": True,
            },
            {
                "section_name": "B",
                "water_source": "Borewell",
                "near_water": True,
            },
            {
                "section_name": "C",
                "water_source": "Canal",
                "near_water": True,
            },
        ],
        "budget": 100000,
        "crop_type": "kharif",
    }

    ml_output = {'recommendations': {'A': [{'crop': 'papaya', 'risk': 0.59, 'budget': 12000}, {'crop': 'banana', 'risk': 0.59, 'budget': 12000}], 'B': [{'crop': 'papaya', 'risk': 0.68, 'budget': 12000}, {'crop': 'potato', 'risk': 0.68, 'budget': 12000}], 'C': [{'crop': 'papaya', 'risk': 0.59, 'budget': 12000}, {'crop': 'banana', 'risk': 0.59, 'budget': 12000}]}, 'expected_profit': {'A': [{'crop': 'papaya', 'expected_profit': 12028.29, 'risk': 0.59, 'cost': 12000}, {'crop': 'banana', 'expected_profit': 11911.6, 'risk': 0.59, 'cost': 12000}], 'B': [{'crop': 'papaya', 'expected_profit': 10076.55, 'risk': 0.68, 'cost': 12000}, {'crop': 'potato', 'expected_profit': 9921.53, 'risk': 0.68, 'cost': 12000}], 'C': [{'crop': 'papaya', 'expected_profit': 12028.29, 'risk': 0.59, 'cost': 12000}, {'crop': 'banana', 'expected_profit': 11911.6, 'risk': 0.59, 'cost': 12000}]}}

    print(recalculate_risk(payload, ml_output))
