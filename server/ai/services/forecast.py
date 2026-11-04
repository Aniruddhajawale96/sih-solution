import os
import requests
from dotenv import load_dotenv
from datetime import datetime
import json

# Load environment variables
load_dotenv()


def get_weather_forecast(location="19.0760,72.8777"):
    """
    Fetch 7-day weather forecast and return simplified JSON
    
    Args:
        location (str): Location coordinates (lat,lon) or city name
                       Default: Mumbai, India (19.0760,72.8777)
    
    Returns:
        dict: Simplified JSON with daily weather summaries
    """
    
    # Get API key from environment
    api_key = os.getenv('WEATHER_API')
    
    if not api_key:
        return {
            "error": True,
            "message": "WEATHER_API key not found in environment variables"
        }
    
    # WeatherAPI endpoint for forecast
    url = "http://api.weatherapi.com/v1/forecast.json"
    
    # Parameters for 7-day forecast
    params = {
        'key': api_key,
        'q': location,
        'days': 7,
        'aqi': 'no',
        'alerts': 'no'
    }
    
    try:
        # Make API request
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        # Process and return simplified JSON
        return process_forecast_data(data)
        
    except requests.exceptions.RequestException as e:
        return {
            "error": True,
            "message": f"Error fetching weather data: {str(e)}",
            "location_requested": location
        }


def process_forecast_data(data):
    """
    Process raw weather data into simplified JSON format
    
    Args:
        data (dict): Raw weather data from API
    
    Returns:
        dict: Simplified daily weather summaries
    """
    
    daily_forecasts = []
    
    for day in data['forecast']['forecastday']:
        day_data = day['day']
        
        # Determine weather condition category
        condition_text = day_data['condition']['text'].lower()
        weather_category = categorize_weather(condition_text)
        
        # Determine rainfall status
        rainfall_status = get_rainfall_status(
            day_data['daily_will_it_rain'],
            day_data['daily_chance_of_rain'],
            day_data['totalprecip_mm']
        )
        
        # Create simplified daily summary
        daily_summary = {
            'day': datetime.strptime(day['date'], '%Y-%m-%d').strftime('%A'),
            'date': day['date'],
            'condition': day_data['condition']['text'],
            'category': weather_category,
            'temp_min_c': day_data['mintemp_c'],
            'temp_max_c': day_data['maxtemp_c'],
            'rainfall_status': rainfall_status,
            'rain_chance': day_data['daily_chance_of_rain'],
            'recommendation': generate_recommendation(day_data, weather_category, rainfall_status)
        }
        
        daily_forecasts.append(daily_summary)
    
    # Return simplified JSON structure
    return {
        'location': data['location']['name'],
        'country': data['location']['country'],
        'forecast': daily_forecasts
    }


def categorize_weather(condition_text):
    """Categorize weather condition into main types"""
    if any(word in condition_text for word in ['sunny', 'clear']):
        return 'sunny'
    elif any(word in condition_text for word in ['partly cloudy', 'partly sunny']):
        return 'partly_cloudy'
    elif any(word in condition_text for word in ['cloudy', 'overcast']):
        return 'cloudy'
    elif any(word in condition_text for word in ['rain', 'drizzle', 'shower']):
        return 'rainy'
    elif any(word in condition_text for word in ['snow', 'sleet', 'blizzard']):
        return 'snowy'
    elif any(word in condition_text for word in ['thunder', 'storm']):
        return 'stormy'
    elif any(word in condition_text for word in ['fog', 'mist', 'haze']):
        return 'foggy'
    else:
        return 'other'


def get_rainfall_status(will_rain, chance_of_rain, precip_mm):
    """Determine rainfall status"""
    if not will_rain:
        return 'no_rain_expected'
    elif chance_of_rain >= 80 and precip_mm >= 5:
        return 'heavy_rain_likely'
    elif chance_of_rain >= 80:
        return 'rain_very_likely'
    elif chance_of_rain >= 50:
        return 'rain_likely'
    elif chance_of_rain >= 30:
        return 'rain_possible'
    else:
        return 'slight_chance_of_rain'


def generate_recommendation(day_data, weather_category, rainfall_status):
    """Generate activity recommendation based on weather"""
    if weather_category == 'sunny' and rainfall_status == 'no_rain_expected':
        return 'Perfect day for outdoor activities!'
    elif weather_category == 'partly_cloudy' and rainfall_status in ['no_rain_expected', 'slight_chance_of_rain']:
        return 'Good day for outdoor plans. Consider bringing a light jacket.'
    elif rainfall_status in ['heavy_rain_likely', 'rain_very_likely']:
        return 'Heavy rain expected. Plan indoor activities and carry an umbrella.'
    elif rainfall_status in ['rain_likely', 'rain_possible']:
        return 'Rain possible. Bring an umbrella and plan backup indoor activities.'
    elif weather_category == 'cloudy':
        return 'Overcast day. Good for indoor/outdoor activities.'
    elif weather_category == 'snowy':
        return 'Snow expected. Dress warmly and drive carefully.'
    elif weather_category == 'stormy':
        return 'Stormy weather. Stay indoors and avoid travel if possible.'
    elif weather_category == 'foggy':
        return 'Foggy conditions. Drive carefully with low visibility.'
    else:
        return 'Check conditions before heading out.'


# Indian cities coordinates
INDIAN_CITIES = {
    'mumbai': '19.0760,72.8777',
    'delhi': '28.6139,77.2090',
    'bangalore': '12.9716,77.5946',
    'chennai': '13.0827,80.2707',
    'kolkata': '22.5726,88.3639',
    'hyderabad': '17.3850,78.4867',
    'pune': '18.5204,73.8567',
    'ahmedabad': '23.0225,72.5714',
    'jaipur': '26.9124,75.7873',
    'surat': '21.1702,72.8311'
}


if __name__ == "__main__":
    # Get forecast for Mumbai (default)
    forecast = get_weather_forecast()
    
    # Print as formatted JSON
    print(json.dumps(forecast, indent=2))
    
    # Also print in readable format
    if 'error' not in forecast:
        print(f"\n{'='*60}")
        print(f"7-Day Weather Forecast for {forecast['location']}, {forecast['country']}")
        print(f"{'='*60}\n")
        
        print(forecast)
        # for day in forecast['forecast']:
        #     print(f"{day['day']}, {day['date']}")
        #     print(f"  Condition: {day['condition']} ({day['category']})")
        #     print(f"  Temperature: {day['temp_min_c']}°C - {day['temp_max_c']}°C")
        #     print(f"  Rainfall: {day['rainfall_status']} ({day['rain_chance']}% chance)")
        #     print(f"  💡 {day['recommendation']}")