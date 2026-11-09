from fastapi import APIRouter, HTTPException, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from pydantic import BaseModel
from typing import Optional
from app.core.database import get_database

router = APIRouter(prefix="/farmer-schemes", tags=["Farmer Schemes"])


# ---------------------------------------------------------------------------
# Dependency
# ---------------------------------------------------------------------------
def get_db() -> AsyncIOMotorDatabase:
    return get_database()


# ---------------------------------------------------------------------------
# Request / Response DTOs
# ---------------------------------------------------------------------------
class FarmerSchemeRequest(BaseModel):
    farmer_id: str


class BankAccount(BaseModel):
    account_number: str
    ifsc_code: str
    bank_name: Optional[str] = None


class FarmerRegisterRequest(BaseModel):
    clerk_id: str
    first_name: str
    last_name: str
    mobile: str
    address: str
    state: str
    bank_account: BankAccount


# ---------------------------------------------------------------------------
# POST /farmer-schemes/register
# ---------------------------------------------------------------------------
@router.post("/register", status_code=201)
async def register_farmer(
    payload: FarmerRegisterRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Register a new farmer document in MongoDB, bridging Clerk identity to a
    MongoDB record.

    Returns the created farmer document (with the new ``_id``).
    """
    farmers_col = db["farmers"]

    # Prevent duplicate registrations for the same Clerk user
    existing = await farmers_col.find_one({"clerk_id": payload.clerk_id})
    if existing:
        raise HTTPException(
            status_code=400,
            detail="A farmer with this Clerk ID is already registered",
        )

    farmer_doc = {
        "clerk_id": payload.clerk_id,
        "first_name": payload.first_name,
        "last_name": payload.last_name,
        "mobile": payload.mobile,
        "address": payload.address,
        "state": payload.state,
        "bank_account": payload.bank_account.model_dump(),
    }

    result = await farmers_col.insert_one(farmer_doc)

    return {
        "success": True,
        "farmer_id": str(result.inserted_id),
        "clerk_id": payload.clerk_id,
    }


# ---------------------------------------------------------------------------
# POST /farmer-schemes/  — get schemes for a farmer
# ---------------------------------------------------------------------------
@router.post("/")
async def get_schemes_for_farmer(
    payload: FarmerSchemeRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Return all schemes applicable to the given farmer."""
    farmers_col = db["farmers"]
    schemes_col = db["schemes"]

    # Convert string → ObjectId
    try:
        farmer_obj_id = ObjectId(payload.farmer_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid farmer ID")

    farmer = await farmers_col.find_one({"_id": farmer_obj_id})
    if not farmer:
        raise HTTPException(status_code=404, detail="Farmer not found")

    state = farmer.get("state")
    latitude = farmer.get("latitude")
    longitude = farmer.get("longitude")

    # Match schemes for this state or national schemes (no state set)
    query = {
        "$or": [
            {"state": state},
            {"state": None},
            {"state": {"$exists": False}},
        ]
    }

    schemes = []
    async for s in schemes_col.find(query):
        s["_id"] = str(s["_id"])
        schemes.append(s)

    return {
        "farmer_id": str(farmer_obj_id),
        "state": state,
        "latitude": latitude,
        "longitude": longitude,
        "schemes": schemes,
    }
