#Entry point, user input loop, and command execution

import geocode
import weather

def main():
    while True:
        location = input("Enter location for controlled burn (or 'exit' to quit): ")
        if location.lower() == 'exit':
            break

        # Geocode location to get lat/lon
        lat, lon = geocode.geocode(location)
        print(f"Coordinates for {location}: {lat}, {lon}")
        
        # Fetch weather data for lat, lon
        print(f"Fetching weather data for {location}...")
        weather_data = weather.get_weather(lat, lon)
        print(f"Weather data for {location}: {weather_data}")

if __name__ == "__main__":
    main()