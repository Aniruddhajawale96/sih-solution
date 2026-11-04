import math
from typing import List, Dict

EARTH_RADIUS = 6378137  # meters (WGS84)


def latlng_to_xy(
    lat: float,
    lng: float,
    origin_lat: float,
    origin_lng: float
) -> Dict[str, float]:
    """
    Converts lat/lng to local cartesian (x, y) in meters
    using equirectangular approximation.
    """

    x = (
        (lng - origin_lng)
        * math.pi
        * EARTH_RADIUS
        / 180
        * math.cos(origin_lat * math.pi / 180)
    )

    y = (
        (lat - origin_lat)
        * math.pi
        * EARTH_RADIUS
        / 180
    )

    return {"x": x, "y": y}


def normalize_polygon(points: List[Dict[str, float]]) -> List[Dict[str, float]]:
    """
    Shifts polygon so all x,y are >= 0 (SVG / Canvas friendly)
    """

    min_x = min(p["x"] for p in points)
    min_y = min(p["y"] for p in points)

    return [
        {
            "x": p["x"] - min_x,
            "y": p["y"] - min_y,
        }
        for p in points
    ]


def project_polygon_to_2d(
    boundary: List[Dict[str, float]]
) -> List[Dict[str, float]]:
    """
    Projects GPS polygon to normalized 2D plane using first point as origin.
    Output is SVG-ready.
    """

    origin = boundary[0]
    origin_lat = origin["latitude"]
    origin_lng = origin["longitude"]

    projected = [
        latlng_to_xy(
            p["latitude"],
            p["longitude"],
            origin_lat,
            origin_lng
        )
        for p in boundary
    ]

    # 🔑 normalize for SVG / UI usage
    return normalize_polygon(projected)
