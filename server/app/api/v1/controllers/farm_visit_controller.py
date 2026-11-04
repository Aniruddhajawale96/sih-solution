from shapely.geometry import Polygon, Point
from app.api.v1.utils.geo_projection import latlng_to_xy, project_polygon_to_2d

MIN_IMAGES = 3
MAX_IMAGES = 5
BASE_BUFFER = 10


def check_farm_visit(boundary, user_location, image_count, gps_accuracy):
    """
    TEMP version:
    - Recomputes projection every request
    - No DB
    """

    # polygon → XY meters
    polygon_xy = project_polygon_to_2d(
        [{"latitude": p.latitude, "longitude": p.longitude} for p in boundary]
    )

    origin = boundary[0]

    polygon = Polygon([(p["x"], p["y"]) for p in polygon_xy])

    # Buffer using GPS tolerance
    buffer_m = max(BASE_BUFFER, gps_accuracy)
    buffered_polygon = polygon.buffer(buffer_m)

    # Convert user location → XY
    user_xy = latlng_to_xy(
        user_location.latitude,
        user_location.longitude,
        origin.latitude,
        origin.longitude,
    )

    user_point = Point(user_xy["x"], user_xy["y"])

    inside = buffered_polygon.contains(user_point) or buffered_polygon.touches(user_point)

    # Decision logic
    if not inside:
        return False, False, False, "You are outside the farm boundary"

    if image_count >= MAX_IMAGES:
        return True, False, True, "Maximum 5 images reached. You can submit."

    if image_count < MIN_IMAGES:
        return True, True, False, "Capture at least 3 images"

    return True, True, True, "Valid farm visit"
