import joblib
import pandas as pd
from ai.services.weather_service import get_future_weather
import os


BASE_DIR = os.path.dirname(__file__)       
MODEL_DIR = os.path.join(BASE_DIR, "models")

crop_model = joblib.load(os.path.join(MODEL_DIR, "crop_model.pkl"))
risk_model = joblib.load(os.path.join(MODEL_DIR, "risk_model.pkl"))
profit_model = joblib.load(os.path.join(MODEL_DIR, "profit_model.pkl"))
encoders = joblib.load(os.path.join(MODEL_DIR, "encoders.pkl"))

def encode_input(data: dict):
    d = data.copy()

    for col in ["soil_type", "water_source", "crop_type"]:
        d[col] = encoders[col].transform([d[col]])[0]

    return d

def recommend_for_section(section, farm, weather):
    results = []

    for crop_name in encoders["crop"].classes_:

        row = {
            "latitude": farm["location"]["latitude"],
            "longitude": farm["location"]["longitude"],
            "soil_type": farm["soil_type"],
            "water_source": section["water_source"],
            "near_water": section["near_water"],
            "budget": farm["budget"],
            "crop_type": farm["crop_type"],
            "temperature": weather["temperature"],
            "rainfall": weather["rainfall"],
            "humidity": weather["humidity"],
            "cost": 12000  # base cost guess (can improve later)
        }

        # encode
        row_encoded = encode_input(row)

        df = pd.DataFrame([row_encoded])

        # predict crop suitability score
        crop_encoded = encoders["crop"].transform([crop_name])[0]
        df_crop = df.copy()
        df_crop["crop"] = crop_encoded

        risk = risk_model.predict(df)[0]
        profit = profit_model.predict(df_crop)[0]

        results.append({
            "crop": crop_name,
            "risk": float(risk),
            "expected_profit": float(profit),
            "budget": row["cost"]
        })

    # sort by profit & risk
    results.sort(key=lambda x: (-x["expected_profit"], x["risk"]))

    return results[:2]  # top 2 crops

def recommend_farm(farm_input, weather):
    recommendations = {}
    expected_profit = {}

    for section in farm_input["soil_sections"]:
        section_name = section["section_name"]

        recs = recommend_for_section(section, farm_input, weather)

        recommendations[section_name] = [
            {
                "crop": r["crop"],
                "risk": round(r["risk"], 2),
                "budget": r["budget"]
            }
            for r in recs
        ]

        expected_profit[section_name] = [
            {
                "crop": r["crop"],
                "expected_profit": round(r["expected_profit"], 2),
                "risk": round(r["risk"], 2),
                "cost": r["budget"]
            }
            for r in recs
        ]

    return {
        "recommendations": recommendations,
        "expected_profit": expected_profit
    }

# farm = {
#     "location": {"latitude": 20.0, "longitude": 77.0},
#     "soil_type": "black soil",
#     "soil_sections": [
#         {"section_name": "A", "water_source": "Canal", "near_water": True},
#         {"section_name": "B", "water_source": "Borewell", "near_water": True},
#         {"section_name": "C", "water_source": "Canal", "near_water": True},
#     ],
#     "budget": 100000,
#     "crop_type": "kharif"
# }

# weather = get_future_weather(20,77)

# output = recommend_farm(farm, weather)
# print(output)