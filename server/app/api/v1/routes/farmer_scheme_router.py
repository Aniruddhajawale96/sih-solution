from fastapi import APIRouter, HTTPException
from pymongo import MongoClient
from bson import ObjectId
from pydantic import BaseModel
import os
from dotenv import load_dotenv

load_dotenv()

MONGODB_URL = os.getenv("MONGODB_URL")
MONGODB_DB = os.getenv("MONGODB_DB")

router = APIRouter(prefix="/farmer-schemes", tags=["Farmer Schemes"])


# -----------------------------
# Request DTO
# -----------------------------
class FarmerSchemeRequest(BaseModel):
    farmer_id: str


# -----------------------------
# DB connection
# -----------------------------
def get_db():
    client = MongoClient(MONGODB_URL, serverSelectionTimeoutMS=5000)
    return client[MONGODB_DB]


# -----------------------------
# POST → Get schemes for farmer
# -----------------------------
@router.post("/")
def get_schemes_for_farmer(payload: FarmerSchemeRequest):
    db = get_db()

    farmers_col = db["farmers"]
    schemes_col = db["schemes"]

    # convert string → ObjectId
    try:
        farmer_obj_id = ObjectId(payload.farmer_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid farmer ID")

    # find farmer using Mongo _id
    farmer = farmers_col.find_one({"_id": farmer_obj_id})

    if not farmer:
        raise HTTPException(status_code=404, detail="Farmer not found")

    state = farmer.get("state")
    latitude = farmer.get("latitude")
    longitude = farmer.get("longitude")

    # state filtering
    query = {
        "$or": [
            {"state": state},
            {"state": None},
            {"state": {"$exists": False}},
        ]
    }

    schemes_cursor = schemes_col.find(query)

    schemes = []
    for s in schemes_cursor:
        s["_id"] = str(s["_id"])
        schemes.append(s)

    return {
        "farmer_id": str(farmer_obj_id),
        "state": state,
        "latitude": latitude,
        "longitude": longitude,
        "schemes": schemes,
    }
