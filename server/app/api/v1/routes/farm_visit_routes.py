from fastapi import APIRouter
from app.api.v1.dtos.farm_validation_dto import (
    FarmVisitCheckRequestDTO,
    FarmVisitCheckResponseDTO,
)
from app.api.v1.controllers.farm_visit_controller import check_farm_visit

router = APIRouter()


@router.post("/visit/check", response_model=FarmVisitCheckResponseDTO)
def validate_visit(payload: FarmVisitCheckRequestDTO):

    inside, can_capture, can_submit, message = check_farm_visit(
        boundary=payload.boundary,
        user_location=payload.user_location,
        image_count=payload.image_count,
        gps_accuracy=payload.gps_accuracy,
    )

    return {
        "inside_boundary": inside,
        "can_capture": can_capture,
        "can_submit": can_submit,
        "message": message,
    }
