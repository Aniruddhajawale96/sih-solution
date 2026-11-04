from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from pymongo import MongoClient
from pymongo.database import Database
from bson import ObjectId
from datetime import datetime
import os
from dotenv import load_dotenv
import shutil
import re
from typing import Optional

load_dotenv()

MONGODB_URL = os.getenv("MONGODB_URL")
MONGODB_DB = "agri-application"
UPLOAD_DIR = "uploads"
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

os.makedirs(UPLOAD_DIR, exist_ok=True)

router = APIRouter(prefix="/applications", tags=["Scheme Applications"])

# Dependency injection for DB
_client: Optional[MongoClient] = None

def get_db() -> Database:
    global _client
    if _client is None:
        _client = MongoClient(MONGODB_URL, serverSelectionTimeoutMS=5000)
    return _client[MONGODB_DB]

def sanitize_filename(filename: str) -> str:
    """Remove dangerous characters from filename"""
    return re.sub(r'[^\w\-.]', '_', filename)

@router.post("/apply/{farmer_id}/{scheme_id}")
async def apply_for_scheme(
    farmer_id: str,
    scheme_id: str,
    zip_file: UploadFile = File(...),
    db: Database = Depends(get_db)
):
    """
    Apply for a scheme by uploading required documents as ZIP
    
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
    farmer = farmers_col.find_one({"_id": farmer_obj_id})
    if not farmer:
        raise HTTPException(status_code=404, detail="Farmer not found")

    # Verify scheme exists
    scheme = schemes_col.find_one({"_id": scheme_obj_id})
    if not scheme:
        raise HTTPException(status_code=404, detail="Scheme not found")

    # Check for duplicate application
    existing_app = applications_col.find_one({
        "farmer_id": farmer_obj_id,
        "scheme_id": scheme_obj_id
    })
    if existing_app:
        raise HTTPException(
            status_code=400, 
            detail="You have already applied for this scheme"
        )

    # Validate file type
    if zip_file.content_type not in ["application/zip", "application/x-zip-compressed"]:
        raise HTTPException(
            status_code=400, 
            detail="Only ZIP files are allowed"
        )

    # Check file size
    file_size = 0
    chunk_size = 1024 * 1024  # 1MB chunks
    temp_path = None
    
    try:
        # Sanitize filename
        safe_filename = sanitize_filename(zip_file.filename or "upload.zip")
        file_name = f"{farmer_id}_{scheme_id}_{datetime.utcnow().timestamp()}_{safe_filename}"
        file_path = os.path.join(UPLOAD_DIR, file_name)
        
        # Save file with size check
        with open(file_path, "wb") as buffer:
            while chunk := await zip_file.read(chunk_size):
                file_size += len(chunk)
                if file_size > MAX_FILE_SIZE:
                    buffer.close()
                    os.remove(file_path)
                    raise HTTPException(
                        status_code=413, 
                        detail=f"File too large. Max size: {MAX_FILE_SIZE / (1024*1024)}MB"
                    )
                buffer.write(chunk)
        
        temp_path = file_path

        # Create application record
        application_doc = {
            "farmer_id": farmer_obj_id,
            "scheme_id": scheme_obj_id,
            "zip_file_path": file_path,
            "file_size": file_size,
            "status": "pending",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

        result = applications_col.insert_one(application_doc)

        return {
            "success": True,
            "message": "Application submitted successfully",
            "application_id": str(result.inserted_id),
            "status": "pending"
        }

    except HTTPException:
        # Cleanup on known errors
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
        raise
    except Exception as e:
        # Cleanup on unexpected errors
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to process application: {str(e)}"
        )

@router.on_event("shutdown")
def shutdown_db():
    """Close DB connection on shutdown"""
    global _client
    if _client:
        _client.close()