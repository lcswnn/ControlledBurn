# Location name -> lat/lon coordinates
from geopy.geocoders import Nominatim

geolocator = Nominatim(user_agent="ControlledBurnApp/1.0", timeout=10)

def geocode(location):
    if not location:
        return None, None
    result = geolocator.geocode(location)
    if result is None:
        raise ValueError(f"Could not find coordinates for '{location}'")
    return result.latitude, result.longitude