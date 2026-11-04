"""
Weather service to fetch future weather data from WeatherAPI.com
"""
import os
import requests
from datetime import datetime, timedelta
from typing import Dict, List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

WEATHER_API_KEY = os.getenv("WEATHER_API") 
WEATHER_API_BASE_URL = "https://api.weatherapi.com/v1"


def get_future_weather(lat: float, lon: float, months: int = 4) -> Dict:
    """
    Fetch future weather forecast from WeatherAPI.com
    
    Args:
        lat: Latitude of the location
        lon: Longitude of the location
        months: Number of months to forecast (default 4)
    
    Returns:
        Dictionary containing weather forecast data
    """
    if not WEATHER_API_KEY or WEATHER_API_KEY == "your_api_key_here":
        print("[DEBUG] WEATHER_API_KEY not set. Using mock data.")
        return _get_mock_weather_data(months)
    
    try:
        # WeatherAPI provides forecast for up to 14 days with free plan
        # For demonstration, we'll fetch the available forecast
        url = f"{WEATHER_API_BASE_URL}/forecast.json"
        
        params = {
            "key": WEATHER_API_KEY,
            "q": f"{lat},{lon}",
            "days": min(14, months * 30),  # Max 14 days for free tier
            "aqi": "no",
            "alerts": "no"
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        
        # Process the weather data
        weather_summary = _process_weather_data(data, months)
        print(f"[DEBUG] Real weather API call successful: {weather_summary}")
        return weather_summary
        
    except Exception as e:
        print(f"[DEBUG] Error fetching weather data: {e}")
        print("[DEBUG] Falling back to mock data")
        return _get_mock_weather_data(months)


def _process_weather_data(api_data: Dict, months: int) -> Dict:
    """
    Process raw API data into a structured format for crop recommendation
    """
    forecast_days = api_data.get("forecast", {}).get("forecastday", [])
    
    if not forecast_days:
        return _get_mock_weather_data(months)
    
    # Calculate averages from available forecast
    total_temp = 0
    total_rainfall = 0
    total_humidity = 0
    total_days = len(forecast_days)
    
    for day in forecast_days:
        day_data = day.get("day", {})
        total_temp += day_data.get("avgtemp_c", 25)
        total_rainfall += day_data.get("totalprecip_mm", 0)
        total_humidity += day_data.get("avghumidity", 60)
    
    avg_temp = total_temp / total_days if total_days > 0 else 25
    total_rainfall_mm = total_rainfall
    avg_humidity = total_humidity / total_days if total_days > 0 else 60
    
    # Extrapolate for the requested months (rough estimation)
    rainfall_per_month = (total_rainfall_mm / total_days) * 30
    total_rainfall_months = rainfall_per_month * months
    
    return {
        "temperature": round(avg_temp, 1),
        "rainfall": round(total_rainfall_months, 1),
        "humidity": round(avg_humidity, 1),
        "forecast_period_days": total_days,
        "months_estimated": months,
        "location": api_data.get("location", {}).get("name", "Unknown")
    }


def _get_mock_weather_data(months: int = 4) -> Dict:
    """
    Fallback mock weather data when API is unavailable
    """
    return {
        "temperature": 28.5,  # Average temperature in Celsius
        "rainfall": 450.0,    # Total rainfall in mm for the period
        "humidity": 65.0,     # Average humidity percentage
        "forecast_period_days": months * 30,
        "months_estimated": months,
        "location": "Mock Location"
    }


if __name__ == "__main__":
    # Test the weather service
    weather = get_future_weather(lat=20.0, lon=77.0, months=4)
    print("Weather Data:")
    print(weather)