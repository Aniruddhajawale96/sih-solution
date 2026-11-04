from pydantic import BaseModel
from app.api.v1.dtos.farm_dto import LatLngDTO


class FarmVisitCheckRequestDTO(BaseModel):
    farm_id: str
    boundary: list[LatLngDTO]
    user_location: LatLngDTO
    image_count: int
    gps_accuracy: float


class FarmVisitCheckResponseDTO(BaseModel):
    inside_boundary: bool
    can_capture: bool
    can_submit: bool
    message: str
