import asyncio
import anyio
from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder
import sys

async def test_geocode(place: str):
    print(f"Testing geocode for: {place}")
    try:
        # Simulate current logic (ASCII Only)
        geolocator = Nominatim(user_agent="avatar_app_test_ascii_geocoder")
        location = await anyio.to_thread.run_sync(lambda: geolocator.geocode(place, timeout=15))
        
        if not location:
            print(f"FAILED: Location not found for {place}")
            return

        print(f"SUCCESS: {location.latitude}, {location.longitude}, {location.address}")
        
        tf = TimezoneFinder()
        tz_name = await anyio.to_thread.run_sync(lambda: tf.timezone_at(lng=location.longitude, lat=location.latitude))
        print(f"TIMEZONE: {tz_name}")
        
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")

if __name__ == "__main__":
    place = sys.argv[1] if len(sys.argv) > 1 else "Moscow"
    asyncio.run(test_geocode(place))
