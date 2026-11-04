from pydantic import BaseModel
from typing import List, Dict


class LatLngDTO(BaseModel):
    latitude: float
    longitude: float


class FarmBoundaryRequestDTO(BaseModel):
    farm_id: str
    boundary: List[LatLngDTO]



class Point2DDTO(BaseModel):
    x: float
    y: float


class AreaDTO(BaseModel):
    square_meters: float
    hectares: float
    acres: float


class FarmBoundaryResponseDTO(BaseModel):
    farm_id: str
    origin: LatLngDTO
    polygon_2d: List[Point2DDTO]
    area: AreaDTO
    zones: List[Dict]
