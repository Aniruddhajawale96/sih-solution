"""
Tornado Alert System - MongoDB Atlas Version with Geocoding
Retrieves farmer data from MongoDB Atlas, geocodes addresses, and sends alerts based on location
"""

from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError, ConnectionFailure
from dotenv import load_dotenv
import os
import requests
import time
from typing import Optional, Tuple

load_dotenv()

MONGODB_ATLAS_URI = os.getenv("MONGODB_URL")
print("DEBUG URI:", MONGODB_ATLAS_URI)

# Database and Collection names
DB_NAME = 'agritech'
COLLECTION_NAME = 'farmers'

# Pune coordinates (tornado location)
PUNE_LAT = 18.5204
PUNE_LONG = 73.8567

# Zone definitions
INNER_ZONE = 0.20  # ±0.20° (~22 km) - Affected area, no alert
OUTER_ZONE = 1.00  # ±1.00° (~111 km) - Warning zone, send alert

# Geocoding cache to avoid duplicate API calls
geocoding_cache = {}

# ============================================================================
# GEOCODING FUNCTIONS
# ============================================================================

def geocode_address(address: str) -> Optional[Tuple[float, float]]:
    """
    Convert address to latitude and longitude using Nominatim (OpenStreetMap)
    Returns (latitude, longitude) or None if geocoding fails
    
    Note: This uses a free service with rate limits. For production:
    - Consider using Google Maps Geocoding API (paid but more reliable)
    - Or LocationIQ, Mapbox, or other geocoding services
    """
    
    # Check cache first
    if address in geocoding_cache:
        return geocoding_cache[address]
    
    try:
        # Using Nominatim (OpenStreetMap) - free but has rate limits
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            'q': address,
            'format': 'json',
            'limit': 1
        }
        headers = {
            'User-Agent': 'TornadoAlertSystem/1.0'  # Required by Nominatim
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                lat = float(data[0]['lat'])
                lon = float(data[0]['lon'])
                
                # Cache the result
                geocoding_cache[address] = (lat, lon)
                
                # Be nice to the free service - add delay
                time.sleep(1)
                
                return (lat, lon)
        
        print(f"  ⚠️  Could not geocode address: {address}")
        return None
        
    except Exception as e:
        print(f"  ❌ Geocoding error for '{address}': {e}")
        return None


def geocode_address_google(address: str, api_key: str) -> Optional[Tuple[float, float]]:
    """
    Alternative: Use Google Maps Geocoding API (requires API key)
    More reliable but requires payment after free tier
    
    To use:
    1. Get API key from: https://console.cloud.google.com/
    2. Enable Geocoding API
    3. Set environment variable: GOOGLE_MAPS_API_KEY
    """
    
    if address in geocoding_cache:
        return geocoding_cache[address]
    
    try:
        url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {
            'address': address,
            'key': api_key
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data['status'] == 'OK' and data['results']:
                location = data['results'][0]['geometry']['location']
                lat = location['lat']
                lon = location['lng']
                
                geocoding_cache[address] = (lat, lon)
                return (lat, lon)
        
        print(f"  ⚠️  Could not geocode address: {address}")
        return None
        
    except Exception as e:
        print(f"  ❌ Geocoding error for '{address}': {e}")
        return None


def update_farmer_coordinates(farmers_collection, farmer_id, latitude, longitude):
    """
    Update farmer record with geocoded coordinates
    """
    try:
        farmers_collection.update_one(
            {'_id': farmer_id},
            {'$set': {
                'latitude': latitude,
                'longitude': longitude,
                'coordinates_updated': True
            }}
        )
        return True
    except Exception as e:
        print(f"  ❌ Error updating coordinates: {e}")
        return False


# ============================================================================
# ALERT FUNCTIONS
# ============================================================================

def test_connection(uri):
    """Test MongoDB Atlas connection"""
    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        print("✓ MongoDB Atlas connection successful")
        client.close()
        return True
    except (ServerSelectionTimeoutError, ConnectionFailure) as e:
        print(f"✗ MongoDB Atlas connection failed: {e}")
        return False


def send_sms(mobile, message):
    """
    Send SMS alert to farmer
    TODO: Integrate with your SMS provider (Twilio, AWS SNS, etc.)
    """
    print(f"  📱 SMS to {mobile}: {message}")
    return True


def geocode_all_farmers():
    """
    Geocode all farmers who don't have coordinates yet
    """
    try:
        client = MongoClient(MONGODB_ATLAS_URI, serverSelectionTimeoutMS=10000)
        db = client[DB_NAME]
        farmers_collection = db[COLLECTION_NAME]
        
        print("\n🗺️  GEOCODING FARMERS")
        print("=" * 70)
        
        # Find farmers without coordinates
        query = {
            '$or': [
                {'latitude': {'$exists': False}},
                {'longitude': {'$exists': False}}
            ],
            'address': {'$exists': True, '$ne': ''}
        }
        
        farmers_to_geocode = list(farmers_collection.find(query))
        total = len(farmers_to_geocode)
        
        print(f"Found {total} farmers to geocode")
        print()
        
        if total == 0:
            print("✓ All farmers already have coordinates!")
            client.close()
            return
        
        success_count = 0
        fail_count = 0
        
        # Option to use Google Maps API if available
        google_api_key = os.getenv('GOOGLE_MAPS_API_KEY')
        use_google = google_api_key is not None
        
        if use_google:
            print("🌍 Using Google Maps Geocoding API")
        else:
            print("🌍 Using OpenStreetMap Nominatim (free, has rate limits)")
            print("   For better results, set GOOGLE_MAPS_API_KEY environment variable")
        
        print()
        
        for i, farmer in enumerate(farmers_to_geocode, 1):
            name = f"{farmer.get('first_name', '')} {farmer.get('last_name', '')}".strip()
            address = farmer.get('address', '')
            
            print(f"[{i}/{total}] Geocoding: {name or 'Unknown'}")
            print(f"  Address: {address}")
            
            # Geocode the address
            if use_google:
                coords = geocode_address_google(address, google_api_key)
            else:
                coords = geocode_address(address)
            
            if coords:
                lat, lon = coords
                print(f"  ✓ Coordinates: ({lat}, {lon})")
                
                # Update database
                if update_farmer_coordinates(farmers_collection, farmer['_id'], lat, lon):
                    success_count += 1
                else:
                    fail_count += 1
            else:
                print(f"  ✗ Failed to geocode")
                fail_count += 1
            
            print()
        
        print("=" * 70)
        print(f"📊 Geocoding Summary:")
        print(f"   Total processed: {total}")
        print(f"   Successfully geocoded: {success_count}")
        print(f"   Failed: {fail_count}")
        print("=" * 70)
        
        client.close()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")


def check_alert_status_from_atlas():
    """
    Retrieve farmers from MongoDB Atlas and check who should receive alerts
    Automatically geocodes addresses if coordinates are missing
    """
    try:
        client = MongoClient(MONGODB_ATLAS_URI, serverSelectionTimeoutMS=10000)
        db = client[DB_NAME]
        farmers_collection = db[COLLECTION_NAME]
        
        print("\n🌪️  TORNADO ALERT SYSTEM - PUNE (MongoDB Atlas)")
        print("=" * 70)
        print(f"Database: {DB_NAME}")
        print(f"Collection: {COLLECTION_NAME}")
        print(f"Tornado Location: Pune (Lat: {PUNE_LAT}, Long: {PUNE_LONG})")
        print(f"Inner Zone (affected, no alert): Lat ±{INNER_ZONE}, Long ±{INNER_ZONE}")
        print(f"Outer Zone (alert sent): Lat ±{OUTER_ZONE}, Long ±{OUTER_ZONE}")
        print("=" * 70)
        print()
        
        # Count total farmers
        total_farmers = farmers_collection.count_documents({})
        print(f"📊 Total farmers in database: {total_farmers}")
        
        # Count farmers with location data
        farmers_with_location = farmers_collection.count_documents({
            'latitude': {'$exists': True},
            'longitude': {'$exists': True}
        })
        print(f"📍 Farmers with coordinates: {farmers_with_location}/{total_farmers}")
        
        # Count farmers without coordinates but with address
        farmers_without_coords = farmers_collection.count_documents({
            '$or': [
                {'latitude': {'$exists': False}},
                {'longitude': {'$exists': False}}
            ],
            'address': {'$exists': True, '$ne': ''}
        })
        
        if farmers_without_coords > 0:
            print(f"⚠️  {farmers_without_coords} farmers need geocoding")
            print(f"\nRun geocoding first? (This will take some time)")
            print(f"You can uncomment the geocode_all_farmers() call in main()")
        
        print()
        
        if farmers_with_location == 0:
            print("❌ No farmers have latitude/longitude data!")
            print("\nOptions:")
            print("1. Run geocoding: Uncomment geocode_all_farmers() in main()")
            print("2. Add coordinates manually in MongoDB")
            return
        
        # Query farmers with coordinates within outer zone
        query = {
            'latitude': {
                '$gte': PUNE_LAT - OUTER_ZONE,
                '$lte': PUNE_LAT + OUTER_ZONE,
                '$exists': True
            },
            'longitude': {
                '$gte': PUNE_LONG - OUTER_ZONE,
                '$lte': PUNE_LONG + OUTER_ZONE,
                '$exists': True
            }
        }
        
        nearby_farmers = list(farmers_collection.find(query))
        print(f"🔍 Farmers within outer zone: {len(nearby_farmers)}")
        print("=" * 70)
        print()
        
        alert_count = 0
        inner_zone_count = 0
        
        for farmer in nearby_farmers:
            f_lat = farmer.get('latitude')
            f_long = farmer.get('longitude')
            
            if f_lat is None or f_long is None:
                continue
            
            name = f"{farmer.get('first_name', '')} {farmer.get('middle_name', '')} {farmer.get('last_name', '')}".strip()
            mobile = farmer.get('mobile', 'N/A')
            address = farmer.get('address', 'Unknown')
            
            # Calculate differences
            lat_diff = abs(f_lat - PUNE_LAT)
            long_diff = abs(f_long - PUNE_LONG)
            
            # Check zones
            in_inner = lat_diff <= INNER_ZONE and long_diff <= INNER_ZONE
            in_outer = lat_diff <= OUTER_ZONE and long_diff <= OUTER_ZONE
            
            # Determine status
            if in_inner:
                status = "🔴 IN AFFECTED AREA - No alert (too close)"
                send_alert = False
                inner_zone_count += 1
            elif in_outer:
                status = "🟡 SEND ALERT - In warning zone"
                send_alert = True
                alert_count += 1
            else:
                status = "🟢 TOO FAR - No alert needed"
                send_alert = False
            
            print(f"Farmer: {name or 'Unknown'}")
            print(f"  Location: {address}")
            print(f"  Coordinates: ({f_lat}, {f_long})")
            print(f"  Distance from Pune: Lat {lat_diff:.4f}°, Long {long_diff:.4f}°")
            print(f"  Status: {status}")
            
            if send_alert:
                msg = "ALERT: Tornado has struck Pune. Please stay safe and take necessary precautions."
                send_sms(mobile, msg)
            
            print()
        
        print("=" * 70)
        print(f"📊 Summary:")
        print(f"   Total farmers processed: {len(nearby_farmers)}")
        print(f"   Farmers in affected area (no alert): {inner_zone_count}")
        print(f"   Alerts sent: {alert_count}")
        print("=" * 70)
        
        client.close()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


def show_sample_farmers():
    """
    Display sample farmers from the database
    """
    try:
        client = MongoClient(MONGODB_ATLAS_URI, serverSelectionTimeoutMS=10000)
        db = client[DB_NAME]
        farmers_collection = db[COLLECTION_NAME]
        
        print("\n📋 Sample Farmers from Database:")
        print("=" * 70)
        
        sample_farmers = farmers_collection.find().limit(5)
        
        for i, farmer in enumerate(sample_farmers, 1):
            print(f"\n{i}. Farmer ID: {farmer.get('_id')}")
            print(f"   Name: {farmer.get('first_name', '')} {farmer.get('middle_name', '')} {farmer.get('last_name', '')}")
            print(f"   Mobile: {farmer.get('mobile', 'N/A')}")
            print(f"   Address: {farmer.get('address', 'N/A')}")
            
            lat = farmer.get('latitude')
            lon = farmer.get('longitude')
            if lat and lon:
                print(f"   Coordinates: ({lat}, {lon})")
            else:
                print(f"   Coordinates: Not geocoded yet")
        
        print("\n" + "=" * 70)
        
        client.close()
        
    except Exception as e:
        print(f"Error: {e}")


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("TORNADO ALERT SYSTEM - MONGODB ATLAS WITH GEOCODING")
    print("=" * 70)
    
    # Test connection first
    print(f"\n🔌 Testing connection to MongoDB Atlas...")
    
    if not test_connection(MONGODB_ATLAS_URI):
        print("\n❌ SETUP REQUIRED:")
        print("   1. Update MONGODB_URL in your .env file")
        print("   2. Whitelist your IP in MongoDB Atlas Network Access")
        print("   3. Verify database user permissions")
        exit(1)
    
    print()
    
    # Show sample farmers
    # show_sample_farmers()
    
    # STEP 1: Geocode all farmers (run this once)
    # Uncomment the line below to geocode addresses to coordinates
    geocode_all_farmers()
    
    # STEP 2: Run the alert system
    check_alert_status_from_atlas()
    
    # print("\n💡 TIPS:")
    # print("   - To geocode farmers: Uncomment geocode_all_farmers() above")
    # print("   - For Google Maps API: Set GOOGLE_MAPS_API_KEY in .env")
    # print("   - OpenStreetMap is free but has rate limits (1 req/sec)")
    # print("   - Coordinates are cached to avoid re-geocoding")