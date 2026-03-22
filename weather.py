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
            "wind_speed_10m",          # needed for hourly gust ratio check
            "precipitation",           # ← NEW: sum past 48h
            "boundary_layer_height",   # ← NEW: mixing height proxy (meters)
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

        # Find current hour index
        current_time = current.get("time")
        hourly_times = hourly.get("time", [])
        current_hour = current_time[:13]
        hour_index = next(
            (i for i, t in enumerate(hourly_times) if t.startswith(current_hour)),
            None
        )

        soil = {}
        precip_48h = None
        mixing_height_ft = None
        hourly_wind_directions = []

        if hour_index is not None:
            # Soil moisture at current hour
            soil = {
                "soil_moisture_0_to_1cm": hourly["soil_moisture_0_to_1cm"][hour_index],
                "soil_moisture_1_to_3cm": hourly["soil_moisture_1_to_3cm"][hour_index],
                "soil_moisture_3_to_9cm": hourly["soil_moisture_3_to_9cm"][hour_index],
            }

            # Sum precipitation over past 48 hours
            start_index = max(0, hour_index - 48)
            precip_48h = sum(
                p for p in hourly["precipitation"][start_index:hour_index]
                if p is not None
            )

            # Mixing height in feet (convert from meters)
            mixing_height_m = hourly["boundary_layer_height"][hour_index]
            if mixing_height_m is not None:
                mixing_height_ft = mixing_height_m * 3.28084

            # Next 12 hours of wind direction for shift detection
            hourly_wind_directions = hourly["wind_direction_10m"][hour_index:hour_index + 12]

        return {
            "temperature_f": current.get("temperature_2m"),
            "relative_humidity": current.get("relative_humidity_2m"),
            "wind_speed_mph": current.get("wind_speed_10m"),
            "wind_gusts_mph": current.get("wind_gusts_10m"),
            "wind_direction_deg": current.get("wind_direction_10m"),
            "precipitation_in": current.get("precipitation"),
            "soil_moisture_0_to_1cm": soil.get("soil_moisture_0_to_1cm"),
            "soil_moisture_1_to_3cm": soil.get("soil_moisture_1_to_3cm"),
            "soil_moisture_3_to_9cm": soil.get("soil_moisture_3_to_9cm"),
            "precip_48h_in": precip_48h,
            "mixing_height_ft": mixing_height_ft,
            "hourly_wind_directions": hourly_wind_directions,
        }

    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")