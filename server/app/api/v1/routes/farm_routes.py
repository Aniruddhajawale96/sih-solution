from fastapi import APIRouter
from app.api.v1.dtos.farm_dto import (
    FarmBoundaryRequestDTO,
    FarmBoundaryResponseDTO,
)
from app.api.v1.controllers.farm_controller import process_farm_boundary

router = APIRouter()

@router.get("/status")
def farm_status():
    return {"status": "working..."}

@router.post(
    "/boundary",
    response_model=FarmBoundaryResponseDTO
)
def handle_farm_boundary(
    payload: FarmBoundaryRequestDTO,
):
    """
    Accept raw GPS boundary from frontend
    """

    return process_farm_boundary(
        farm_id=payload.farm_id,
        boundary=payload.boundary,
    )
