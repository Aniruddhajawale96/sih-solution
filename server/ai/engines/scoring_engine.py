import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
CROP_PATH = os.path.join(BASE_DIR, "config", "crop_db.json")

with open(CROP_PATH) as f:
    CROP_DB = json.load(f)

def score_crops(crops, payload, weather):
    scored = []

    avg_temp = weather["avg_temp"]
    total_rain = weather["total_rain"]
    humidity = weather["avg_humidity"]
    avg_rain = sum(weather["rain"]) / len(weather["rain"])

    for crop in crops:
        data = CROP_DB[crop]

        score = 0

        # weather suitability
        if avg_rain > 50 and data["water_need"] == "high":
            score += 3
        if avg_rain < 20 and data["water_need"] == "low":
            score += 3

        # budget
        if data["cost"] <= payload["budget"]:
            score += 2

        scored.append({
            "crop": crop,
            "score": score,
            "cost": data["cost"],
            "water_need": data["water_need"],
            "risk": data["base_risk"]
        })

    return scored
