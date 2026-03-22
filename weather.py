import requests
from datetime import datetime

def get_weather(lat, lon):
    BASE_URL = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": [
            "temperature_2m",
            "relative_humidity_2m",
            "wind_speed_10m",
            "wind_gusts_10m",
            "wind_direction_10m",
            "precipitation"
        ],
        "hourly": [
            "wind_direction_10m",
            "soil_moisture_0_to_1cm",
            "soil_moisture_1_to_3cm",
            "soil_moisture_3_to_9cm"
        ],
        "past_days": 2,
        "wind_speed_unit": "mph",
        "temperature_unit": "fahrenheit",
        "precipitation_unit": "inch",
        "timezone": "America/Chicago"
    }

    try:
        response = requests.get(BASE_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        current = data.get("current", {})
        hourly = data.get("hourly", {})

        # Find the index of the current hour in the hourly time list
        current_time = current.get("time")  # e.g. "2026-03-22T12:00"
        hourly_times = hourly.get("time", [])
        
        # Match current hour (trim minutes off current time)
        current_hour = current_time[:13]  # "2026-03-22T12"
        hour_index = next(
            (i for i, t in enumerate(hourly_times) if t.startswith(current_hour)),
            None
        )

        soil = {}
        if hour_index is not None:
            soil = {
                "soil_moisture_0_to_1cm":  hourly["soil_moisture_0_to_1cm"][hour_index],
                "soil_moisture_1_to_3cm":  hourly["soil_moisture_1_to_3cm"][hour_index],
                "soil_moisture_3_to_9cm":  hourly["soil_moisture_3_to_9cm"][hour_index],
            }

        print("Current:", current)
        print("Soil:", soil)

        return current, soil

    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")