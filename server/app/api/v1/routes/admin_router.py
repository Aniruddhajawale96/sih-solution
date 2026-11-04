from fastapi import APIRouter, HTTPException, Depends
from bson import ObjectId
from app.api.v1.dtos.admin_dto import SchemeCreateDTO, SchemeResponseDTO
from app.core.database import get_database

router = APIRouter(tags=["Admin"])


# Get scheme by ID
@router.get("/scheme/{scheme_id}", response_model=SchemeResponseDTO)
async def get_scheme_by_id(scheme_id: str, db=Depends(get_database)):
    if not ObjectId.is_valid(scheme_id):
        raise HTTPException(status_code=400, detail="Invalid scheme ID")

    scheme = await db.schemes.find_one({"_id": ObjectId(scheme_id)})

    if not scheme:
        raise HTTPException(status_code=404, detail="Scheme not found")

    scheme["_id"] = str(scheme["_id"])  # convert ObjectId → string
    return scheme


# Create new scheme
@router.post("/scheme", response_model=SchemeResponseDTO)
async def create_scheme(payload: SchemeCreateDTO, db=Depends(get_database)):
    result = await db.schemes.insert_one(payload.model_dump())

    scheme = await db.schemes.find_one({"_id": result.inserted_id})
    scheme["_id"] = str(scheme["_id"])  # convert ObjectId → string

    return scheme
