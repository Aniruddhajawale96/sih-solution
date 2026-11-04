"""
Main AI module for crop recommendation system
"""

try:
    # When used as part of a package (preferred)
    from .engines.recommendation_engine import recommend_crops
    from .engines.profit_engine import calculate_expected_profit
    from .services.weather_service import get_future_weather
except ImportError:  # pragma: no cover - fallback for direct script execution
    # When run directly as `python -m ai.main` or similar
    from ai.engines.recommendation_engine import recommend_crops  # type: ignore
    from ai.engines.profit_engine import calculate_expected_profit  # type: ignore
    from ai.services.weather_service import get_future_weather  # type: ignore


def _build_internal_payload(external_payload: dict) -> dict:
    """
    Transform external API payload to internal format
    """
    soil_sections = external_payload.get("soil_sections", [])
    sections = [s["section_name"] for s in soil_sections]

    internal = {
        "location": external_payload.get("location"),
        "soil_type": external_payload.get("soil_type"),
        "soil_sections": soil_sections,
        "sections": sections,
        "budget": external_payload.get("budget", 0),
        # normalise crop_type into the `season` field used internally
        "season": (external_payload.get("crop_type") or "").lower(),
    }

    return internal


def run_ai(payload: dict):
    """
    Run crop recommendation AI
    
    Args:
        payload: Dictionary containing location, soil_type, soil_sections, budget, crop_type
    
    Returns:
        Dictionary of crop recommendations by section
    """
    internal_payload = _build_internal_payload(payload)

    # Extract latitude and longitude from location
    location = internal_payload.get("location", {})
    if isinstance(location, dict):
        lat = location.get("latitude", 0.0)
        lon = location.get("longitude", 0.0)
    elif isinstance(location, (list, tuple)) and len(location) == 2:
        lat, lon = location
    else:
        lat, lon = 0.0, 0.0

    # Get weather forecast
    weather = get_future_weather(
        lat=lat,
        lon=lon,
        months=4,
    )

    result = recommend_crops(internal_payload, weather)
    return result


def run_ai_with_profit(payload: dict):
    """
    Run crop recommendation AI with profit calculations
    
    Args:
        payload: Dictionary containing location, soil_type, soil_sections, budget, crop_type
    
    Returns:
        Dictionary with 'recommendations' and 'expected_profit' keys
    """
    internal_payload = _build_internal_payload(payload)

    # Extract latitude and longitude from location
    location = internal_payload.get("location", {})
    if isinstance(location, dict):
        lat = location.get("latitude", 0.0)
        lon = location.get("longitude", 0.0)
    elif isinstance(location, (list, tuple)) and len(location) == 2:
        lat, lon = location
    else:
        lat, lon = 0.0, 0.0

    # Get weather forecast
    weather = get_future_weather(
        lat=lat,
        lon=lon,
        months=4,
    )

    recommendations = recommend_crops(internal_payload, weather)
    expected_profit = calculate_expected_profit(internal_payload, recommendations)

    return {
        "recommendations": recommendations,
        "expected_profit": expected_profit,
    }


if __name__ == "__main__":
    # Example payload with latitude/longitude
    example_payload = {
        "location": {"latitude": 20.0, "longitude": 77.0},  # Nashik coordinates
        "soil_type": "Black Soil",
        "soil_sections": [
            {
                "section_name": "A",
                "water_source": "Canal",
                "near_water": True,
            },
            {
                "section_name": "B",
                "water_source": "Borewell",
                "near_water": True,
            },
            {
                "section_name": "C",
                "water_source": "Canal",
                "near_water": True,
            },
        ],
        "budget": 100000,
        "crop_type": "Kharif",
    }

    # Show recommendations only
    print("=" * 60)
    print("CROP RECOMMENDATIONS")
    print("=" * 60)
    output = run_ai(example_payload)
    import json
    print(json.dumps(output, indent=2))

    # Show recommendations + expected profit
    print("\n" + "=" * 60)
    print("RECOMMENDATIONS WITH EXPECTED PROFIT")
    print("=" * 60)
    result = run_ai_with_profit(example_payload)
    print(json.dumps(result, indent=2))