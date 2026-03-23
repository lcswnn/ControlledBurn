import requests
import time
from datetime import datetime, timedelta

MAX_RETRIES = 3
BASE_DELAY = 2  # seconds


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
            "wind_speed_10m",
            "precipitation",
            "boundary_layer_height",
            "soil_moisture_0_to_1cm",
            "soil_moisture_1_to_3cm",
            "soil_moisture_3_to_9cm",
            "soil_moisture_9_to_27cm",
            "soil_moisture_27_to_81cm"
        ],
        "past_days": 2,
        "wind_speed_unit": "mph",
        "temperature_unit": "fahrenheit",
        "precipitation_unit": "inch",
        "timezone": "America/Chicago"
    }

    # ── Fetch with retry + exponential backoff ────────────────────────────────
    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(BASE_URL, params=params, timeout=10)

            if response.status_code == 429:
                wait = BASE_DELAY * (2 ** attempt)  # 2s, 4s, 8s
                if attempt < MAX_RETRIES - 1:
                    time.sleep(wait)
                    continue
                else:
                    raise RuntimeError(
                        f"Non-successful status code 429 — rate limit exceeded "
                        f"after {MAX_RETRIES} retries"
                    )

            response.raise_for_status()
            data = response.json()
            break  # success

        except requests.exceptions.RequestException as e:
            last_error = e
            if attempt < MAX_RETRIES - 1:
                time.sleep(BASE_DELAY * (2 ** attempt))
                continue
            raise RuntimeError(f"Weather API request failed after {MAX_RETRIES} attempts: {e}")
    else:
        raise RuntimeError(f"Weather API request failed: {last_error}")

    # ── Parse response ────────────────────────────────────────────────────────
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
            "soil_moisture_9_to_27cm": hourly["soil_moisture_9_to_27cm"][hour_index],
            "soil_moisture_27_to_81cm": hourly["soil_moisture_27_to_81cm"][hour_index]
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
        "soil_moisture_9_to_27cm": soil.get("soil_moisture_9_to_27cm"),
        "soil_moisture_27_to_81cm": soil.get("soil_moisture_27_to_81cm"),
        "precip_48h_in": precip_48h,
        "mixing_height_ft": mixing_height_ft,
        "hourly_wind_directions": hourly_wind_directions,
    }


def get_weekly_forecast(lat, lon, days=7):
    """Fetch daily forecast data for the next `days` days.

    Returns a list of dicts, one per day, with the fields that
    conditions.py needs to run threshold checks.
    """
    BASE_URL = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": [
            "temperature_2m_max",
            "temperature_2m_min",
            "wind_speed_10m_max",
            "wind_gusts_10m_max",
            "wind_direction_10m_dominant",
            "relative_humidity_2m_max",
            "relative_humidity_2m_min",
            "relative_humidity_2m_mean",
            "precipitation_sum",
            "precipitation_probability_max",
        ],
        "hourly": [
            "wind_direction_10m",
            "boundary_layer_height",
            "soil_moisture_0_to_1cm",
            "soil_moisture_1_to_3cm",
            "soil_moisture_3_to_9cm",
            "soil_moisture_9_to_27cm",
            "soil_moisture_27_to_81cm",
        ],
        "forecast_days": days,
        "wind_speed_unit": "mph",
        "temperature_unit": "fahrenheit",
        "precipitation_unit": "inch",
        "timezone": "America/Chicago",
    }

    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(BASE_URL, params=params, timeout=10)
            if response.status_code == 429:
                wait = BASE_DELAY * (2 ** attempt)
                if attempt < MAX_RETRIES - 1:
                    time.sleep(wait)
                    continue
                else:
                    raise RuntimeError(
                        f"Rate limit exceeded after {MAX_RETRIES} retries"
                    )
            response.raise_for_status()
            data = response.json()
            break
        except requests.exceptions.RequestException as e:
            last_error = e
            if attempt < MAX_RETRIES - 1:
                time.sleep(BASE_DELAY * (2 ** attempt))
                continue
            raise RuntimeError(f"Weather API failed after {MAX_RETRIES} attempts: {e}")
    else:
        raise RuntimeError(f"Weather API failed: {last_error}")

    daily = data.get("daily", {})
    hourly = data.get("hourly", {})
    hourly_times = hourly.get("time", [])

    dates = daily.get("time", [])
    forecasts = []

    for i, date_str in enumerate(dates):
        # Find the hourly indices that belong to this day (midday ≈ 12:00 local)
        midday_key = f"{date_str}T12:00"
        mid_idx = next(
            (j for j, t in enumerate(hourly_times) if t.startswith(midday_key)),
            None,
        )

        # Soil moisture — use midday value or first available for the day
        day_start_key = f"{date_str}T"
        day_indices = [j for j, t in enumerate(hourly_times) if t.startswith(day_start_key)]
        soil_idx = mid_idx if mid_idx is not None else (day_indices[0] if day_indices else None)

        soil = {}
        if soil_idx is not None:
            for layer in ("soil_moisture_0_to_1cm", "soil_moisture_1_to_3cm",
                          "soil_moisture_3_to_9cm", "soil_moisture_9_to_27cm",
                          "soil_moisture_27_to_81cm"):
                vals = hourly.get(layer, [])
                soil[layer] = vals[soil_idx] if soil_idx < len(vals) else None

        # Mixing height — use midday value
        mixing_height_ft = None
        if mid_idx is not None:
            blh = hourly.get("boundary_layer_height", [])
            if mid_idx < len(blh) and blh[mid_idx] is not None:
                mixing_height_ft = blh[mid_idx] * 3.28084

        # Wind directions for the day (for frontal passage check)
        day_wind_dirs = []
        if day_indices:
            wd = hourly.get("wind_direction_10m", [])
            day_wind_dirs = [wd[j] for j in day_indices if j < len(wd) and wd[j] is not None]

        # Use mean of min/max for representative temp & humidity
        t_max = daily["temperature_2m_max"][i]
        t_min = daily["temperature_2m_min"][i]
        rh_max = daily["relative_humidity_2m_max"][i]
        rh_min = daily["relative_humidity_2m_min"][i]
        rh_mean = daily.get("relative_humidity_2m_mean", [None] * len(dates))[i]

        forecasts.append({
            "date": date_str,
            "temperature_f": round((t_max + t_min) / 2, 1) if t_max and t_min else None,
            "temperature_max_f": t_max,
            "temperature_min_f": t_min,
            "relative_humidity": rh_mean if rh_mean else (
                round((rh_max + rh_min) / 2) if rh_max and rh_min else None
            ),
            "relative_humidity_max": rh_max,
            "relative_humidity_min": rh_min,
            "wind_speed_mph": daily["wind_speed_10m_max"][i],
            "wind_gusts_mph": daily["wind_gusts_10m_max"][i],
            "wind_direction_deg": daily["wind_direction_10m_dominant"][i],
            "precipitation_in": daily["precipitation_sum"][i],
            "precipitation_probability": daily.get("precipitation_probability_max", [None] * len(dates))[i],
            "soil_moisture_0_to_1cm": soil.get("soil_moisture_0_to_1cm"),
            "soil_moisture_1_to_3cm": soil.get("soil_moisture_1_to_3cm"),
            "soil_moisture_3_to_9cm": soil.get("soil_moisture_3_to_9cm"),
            "soil_moisture_9_to_27cm": soil.get("soil_moisture_9_to_27cm"),
            "soil_moisture_27_to_81cm": soil.get("soil_moisture_27_to_81cm"),
            "mixing_height_ft": mixing_height_ft,
            "hourly_wind_directions": day_wind_dirs,
        })

    return forecasts