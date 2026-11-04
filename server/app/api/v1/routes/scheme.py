from fastapi import APIRouter, HTTPException
from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URL = os.getenv("MONGO_URL")

if not MONGO_URL:
    raise ValueError("MONGO_URL not found in .env")

router = APIRouter(prefix="/schemes", tags=["schemes"])

print("Connected to MongoDB")

def get_db():
    try:
        client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000)
        return client["agri_db"]
    except Exception as e:
        print("Mongo connection error:", e)
        raise HTTPException(status_code=503, detail="DB connection failed")

def get_schemes_for_farmer(farmer_id: str):
    print("\n--- DEBUG START ---")
    print("Farmer ID:", farmer_id)

    db = get_db()

    farmers_col = db["farmers"]
    schemes_col = db["schemes"]

    # 1️⃣ get farmer
    farmer = farmers_col.find_one({"id": farmer_id})

    if not farmer:
        raise HTTPException(status_code=404, detail="Farmer not found")

    state = farmer.get("state")
    print("Farmer state:", state)

    query = {
        "$or": [
            {"state": state},
            {"state": None},
            {"state": {"$exists": False}}
        ]
    }

    schemes_cursor = schemes_col.find(query)

    schemes_list = []
    for s in schemes_cursor:
        s["_id"] = str(s["_id"])  # convert ObjectId
        schemes_list.append(s)

    return {
        "farmer_id": farmer_id,
        "state": state,
        "schemes": schemes_list
    }

@router.get("/farmer/{farmer_id}")
def api_get_schemes(farmer_id: str):
    return get_schemes_for_farmer(farmer_id)

if __name__ == "__main__":
    test_id = "835c2d5b-13e1-408c-abc5-13a74affc911"
    print(get_schemes_for_farmer(test_id))