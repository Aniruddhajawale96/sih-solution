from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from datetime import datetime
import os
import re
from app.core.database import get_database

UPLOAD_DIR = "uploads"
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

os.makedirs(UPLOAD_DIR, exist_ok=True)

router = APIRouter(prefix="/applications", tags=["Scheme Applications"])


def get_db() -> AsyncIOMotorDatabase:
    return get_database()


def sanitize_filename(filename: str) -> str:
    """Remove dangerous characters from filename."""
    return re.sub(r'[^\w\-.]', '_', filename)


@router.post("/apply/{farmer_id}/{scheme_id}")
async def apply_for_scheme(
    farmer_id: str,
    scheme_id: str,
    zip_file: UploadFile = File(...),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Apply for a scheme by uploading required documents as ZIP.

    - **farmer_id**: MongoDB ObjectId of the farmer
    - **scheme_id**: MongoDB ObjectId of the scheme
    - **zip_file**: ZIP file containing all required documents
    """
    farmers_col = db["farmers"]
    schemes_col = db["schemes"]
    applications_col = db["scheme_applications"]

    # Validate ObjectId format
    try:
        farmer_obj_id = ObjectId(farmer_id)
        scheme_obj_id = ObjectId(scheme_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    # Verify farmer exists
    farmer = await farmers_col.find_one({"_id": farmer_obj_id})
    if not farmer:
        raise HTTPException(status_code=404, detail="Farmer not found")

    # Verify scheme exists
    scheme = await schemes_col.find_one({"_id": scheme_obj_id})
    if not scheme:
        raise HTTPException(status_code=404, detail="Scheme not found")

    # Check for duplicate application
    existing_app = await applications_col.find_one({
        "farmer_id": farmer_obj_id,
        "scheme_id": scheme_obj_id,
    })
    if existing_app:
        raise HTTPException(
            status_code=400,
            detail="You have already applied for this scheme",
        )

    # Validate file type
    if zip_file.content_type not in ["application/zip", "application/x-zip-compressed"]:
        raise HTTPException(status_code=400, detail="Only ZIP files are allowed")

    temp_path = None
    file_size = 0
    chunk_size = 1024 * 1024  # 1MB chunks

    try:
        safe_filename = sanitize_filename(zip_file.filename or "upload.zip")
        file_name = f"{farmer_id}_{scheme_id}_{datetime.utcnow().timestamp()}_{safe_filename}"
        file_path = os.path.join(UPLOAD_DIR, file_name)

        # Save file while checking size
        with open(file_path, "wb") as buffer:
            while chunk := await zip_file.read(chunk_size):
                file_size += len(chunk)
                if file_size > MAX_FILE_SIZE:
                    buffer.close()
                    os.remove(file_path)
                    raise HTTPException(
                        status_code=413,
                        detail=f"File too large. Max size: {MAX_FILE_SIZE / (1024 * 1024)}MB",
                    )
                buffer.write(chunk)

        temp_path = file_path

        application_doc = {
            "farmer_id": farmer_obj_id,
            "scheme_id": scheme_obj_id,
            "zip_file_path": file_path,
            "file_size": file_size,
            "status": "pending",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

        result = await applications_col.insert_one(application_doc)

        return {
            "success": True,
            "message": "Application submitted successfully",
            "application_id": str(result.inserted_id),
            "status": "pending",
        }

    except HTTPException:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
        raise
    except Exception as e:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process application: {str(e)}",
        )
