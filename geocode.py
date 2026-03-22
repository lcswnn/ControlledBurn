#Location name -> lat/lon coordinates
from geopy.geocoders import Nominatim

def geocode(location):
    geolocator = Nominatim(user_agent="my_geopy_app")
    if location:
      location = geolocator.geocode(location)
      return location.latitude, location.longitude
    else:
        return None, None