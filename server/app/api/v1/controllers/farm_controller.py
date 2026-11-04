# controllers/farm_controller.py

from typing import List
from app.api.v1.dtos.farm_dto import (
    LatLngDTO,
    FarmBoundaryResponseDTO,
    AreaDTO,
)
from app.api.v1.utils.geo_projection import project_polygon_to_2d
from app.api.v1.utils.area import calculate_polygon_area, to_hectares, to_acres


def close_polygon(boundary: List[LatLngDTO]) -> List[LatLngDTO]:
    """Ensure polygon is closed."""
    if boundary[0] != boundary[-1]:
        return boundary + [boundary[0]]
    return boundary


def process_farm_boundary(
    farm_id: str,
    boundary: List[LatLngDTO],
) -> FarmBoundaryResponseDTO:
    """
    Core domain logic:
    - Close polygon
    - Project GPS → 2D
    - Calculate area
    """

    closed_boundary = close_polygon(boundary)

    boundary_dicts = [p.dict() for p in closed_boundary]

    # latlang to → 2D
    polygon_2d = project_polygon_to_2d(boundary_dicts)

    # Area calculation for frontend
    area_m2 = calculate_polygon_area(polygon_2d)

    area = AreaDTO(
        square_meters=area_m2,
        hectares=to_hectares(area_m2),
        acres=to_acres(area_m2),
    )

    return FarmBoundaryResponseDTO(
        farm_id=farm_id,
        origin=closed_boundary[0],
        polygon_2d=polygon_2d,
        area=area,
        zones=[], 
    )
