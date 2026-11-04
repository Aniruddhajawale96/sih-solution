def calculate_polygon_area(coords):
    area = 0.0
    n = len(coords)

    for i in range(n):
        j = (i + 1) % n
        area += coords[i]["x"] * coords[j]["y"]
        area -= coords[j]["x"] * coords[i]["y"]

    return abs(area) / 2


def to_hectares(area_m2):
    return area_m2 / 10_000


def to_acres(area_m2):
    return area_m2 / 4046.86
