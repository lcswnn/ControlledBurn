# Threshold logic, returns pass/fail per condition
import config
import requests

def check_wind(wind_speed_mph, wind_gust_mph, wind_direction_deg, prev_wind_direction_deg):
    if wind_speed_mph < config.WIND_SPEED_MIN_MPH:
        return False, "Wind speed is too low for a controlled burn."

    if wind_speed_mph > config.WIND_SPEED_MAX_MPH:
        return False, "Wind speed is too high for a controlled burn."

    if wind_gust_mph / max(wind_speed_mph, 0.1) > config.WIND_GUST_MAX_RATIO:
        return False, "Wind gusts are too strong relative to sustained wind speed."

    if prev_wind_direction_deg is not None:
        shift = abs(wind_direction_deg - prev_wind_direction_deg)
        shift = min(shift, 360 - shift)
        if shift > config.WIND_DIRECTION_SHIFT_MAX_DEG:
            return False, "Wind direction has shifted too much recently."

    return True, "Wind conditions are acceptable for a controlled burn."

def check_humidity(relative_humidity, fuel_height_ft):
    if fuel_height_ft <= config.FUEL_HEIGHT_SHORT_THRESHOLD_FT:  # e.g. 2.0 ft
        rh_min = config.RH_MIN_SHORT_FUEL
        rh_max = config.RH_MAX_SHORT_FUEL
    else:
        rh_min = config.RH_MIN_TALL_FUEL
        rh_max = config.RH_MAX_TALL_FUEL

    if relative_humidity < rh_min:
        return False, f"Humidity {relative_humidity}% is too low for {'tall' if fuel_height_ft > 2 else 'short'} fuel."

    if relative_humidity > rh_max:
        return False, f"Humidity {relative_humidity}% is too high for {'tall' if fuel_height_ft > 2 else 'short'} fuel."

    return True, "Humidity is acceptable for current fuel conditions."

def check_fuel_height():
    try:
        height = float(input("Enter fuel/vegetation height in feet: "))
    except ValueError:
        return False, "Invalid input for fuel height."

    if height > config.FUEL_HEIGHT_MAX_FT:
        return False, "Fuel height is too tall — risk of uncontrollable fire behavior."

    if height < config.FUEL_HEIGHT_MIN_FT:
        return False, "Fuel height is too short — may not sustain a controlled burn."

    return True, "Fuel height is acceptable for a controlled burn."

def check_temp(temperature_f, fuel_height_ft):
    if fuel_height_ft <= config.FUEL_HEIGHT_SHORT_THRESHOLD_FT:
        temp_min = config.TEMP_MIN_SHORT_FUEL_F
        temp_max = config.TEMP_MAX_SHORT_FUEL_F
    else:
        temp_min = config.TEMP_MIN_TALL_FUEL_F
        temp_max = config.TEMP_MAX_TALL_FUEL_F

    if temperature_f < temp_min:
        return False, f"Temperature {temperature_f}°F is too low for {'tall' if fuel_height_ft > config.FUEL_HEIGHT_SHORT_THRESHOLD_FT else 'short'} fuel."

    if temperature_f > temp_max:
        return False, f"Temperature {temperature_f}°F is too high for {'tall' if fuel_height_ft > config.FUEL_HEIGHT_SHORT_THRESHOLD_FT else 'short'} fuel."

    return True, "Temperature conditions are acceptable for a controlled burn."

def check_6040_rule(temperature_f, relative_humidity, wind_speed_mph):
    temp_ok = temperature_f <= config.RULE_6040_TEMP_MAX_F
    rh_ok = relative_humidity >= config.RULE_6040_RH_MIN_PCT
    wind_ok = config.WIND_SPEED_MIN_MPH <= wind_speed_mph <= config.WIND_SPEED_MAX_MPH

    if temp_ok and rh_ok and wind_ok:
        return True, "60/40 rule satisfied — conservative conditions met."

    reasons = []
    if not temp_ok:
        reasons.append(f"temp {temperature_f}°F exceeds 60°F")
    if not rh_ok:
        reasons.append(f"humidity {relative_humidity}% is below 40%")
    if not wind_ok:
        reasons.append(f"wind {wind_speed_mph} mph outside 5-15 mph range")

    return False, f"60/40 rule NOT met: {', '.join(reasons)}. Proceed with extra caution."

def check_soil(soil_moisture_0_to_1cm, soil_moisture_1_to_3cm, soil_moisture_3_to_9cm, soil_moisture_9_to_27cm, soil_moisture_27_to_81cm):
    layers = [
        (soil_moisture_0_to_1cm, "Surface (0-1cm)"),
        (soil_moisture_1_to_3cm, "Shallow (1-3cm)"),
        (soil_moisture_3_to_9cm, "Mid (3-9cm)"),
        (soil_moisture_9_to_27cm, "Deep (9-27cm)"),
        (soil_moisture_27_to_81cm, "Deep (27-81cm)"),
    ]

    for value, label in layers:
        if value is None:
            continue
        if value < config.SOIL_MOISTURE_MIN:
            return False, f"{label} soil moisture is too low for a controlled burn."
        if value > config.SOIL_MOISTURE_IDEAL:
            return False, f"{label} soil moisture is too high for a controlled burn."

    return True, "Soil moisture is acceptable for a controlled burn."

def check_smoke_dispersal(mixing_height_ft, transport_wind_mph):
    if mixing_height_ft < config.MIXING_HEIGHT_MIN_FT:
        return False, "Mixing height is too low for good smoke dispersal."

    if mixing_height_ft > config.MIXING_HEIGHT_MAX_FT:
        return False, "Mixing height is unusually high — check for data accuracy."

    if transport_wind_mph < config.TRANSPORT_WIND_MIN_MPH:
        return False, "Transport wind speed is too low for effective smoke dispersal."
    
    if transport_wind_mph > config.TRANSPORT_WIND_MAX_MPH:
        return False, "Transport wind speed is too high — may cause smoke to spread too rapidly."

    return True, "Smoke dispersal conditions are acceptable for a controlled burn."

def check_frontal_passage(hourly_wind_directions):
    if len(hourly_wind_directions) < config.FRONTAL_PASSAGE_WINDOW_HRS:
        return False, "Not enough hourly wind direction data to assess frontal passage."

    initial_direction = hourly_wind_directions[0]  # ✅ this IS the current hour
    for i in range(1, len(hourly_wind_directions)):
        shift = abs(hourly_wind_directions[i] - initial_direction)
        shift = min(shift, 360 - shift)
        if shift > config.WIND_DIRECTION_SHIFT_MAX_DEG:
            return True, f"Significant wind shift detected ~{i}hrs from now — possible frontal passage."

    return False, "No significant wind direction shift detected in the next 12 hours."

def calculate_burn_score(weather_data, fuel_height, condition_results, condition_red_flag):

    def _range_score(value, ideal_low, ideal_high, fail_low, fail_high):
        if value is None:
            return 50  # unknown → neutral
        if ideal_low <= value <= ideal_high:
            return 100
        if value < ideal_low:
            if fail_low is None or fail_low >= ideal_low:
                return 0
            return max(0, 100 * (value - fail_low) / (ideal_low - fail_low))
        # value > ideal_high
        if fail_high is None or fail_high <= ideal_high:
            return 0
        return max(0, 100 * (fail_high - value) / (fail_high - ideal_high))

    ws = weather_data["wind_speed_mph"] or 0
    wg = weather_data["wind_gusts_mph"] or 0
    rh = weather_data["relative_humidity"] or 0
    temp = weather_data["temperature_f"] or 0
    mix_h = weather_data["mixing_height_ft"]
    sm = weather_data["soil_moisture_0_to_1cm"]

    # --- Wind speed sub-score ---
    wind_score = _range_score(ws,
        config.WIND_SPEED_MIN_MPH, config.WIND_SPEED_MAX_MPH,
        0, config.WIND_SPEED_MAX_MPH + 10)

    # Penalize excessive gust ratio
    gust_ratio = wg / max(ws, 0.1)
    if gust_ratio > config.WIND_GUST_MAX_RATIO:
        wind_score *= max(0, 1 - (gust_ratio - config.WIND_GUST_MAX_RATIO))

    # --- Humidity sub-score ---
    if fuel_height <= config.FUEL_HEIGHT_SHORT_THRESHOLD_FT:
        rh_min, rh_max = config.RH_MIN_SHORT_FUEL, config.RH_MAX_SHORT_FUEL
    else:
        rh_min, rh_max = config.RH_MIN_TALL_FUEL, config.RH_MAX_TALL_FUEL
    humidity_score = _range_score(rh, rh_min, rh_max, rh_min - 15, rh_max + 20)

    # --- Temperature sub-score ---
    if fuel_height <= config.FUEL_HEIGHT_SHORT_THRESHOLD_FT:
        t_min, t_max = config.TEMP_MIN_SHORT_FUEL_F, config.TEMP_MAX_SHORT_FUEL_F
    else:
        t_min, t_max = config.TEMP_MIN_TALL_FUEL_F, config.TEMP_MAX_TALL_FUEL_F
    temp_score = _range_score(temp, t_min, t_max, t_min - 15, t_max + 15)

    # --- Soil moisture sub-score ---
    soil_score = _range_score(sm,
        config.SOIL_MOISTURE_MIN, config.SOIL_MOISTURE_IDEAL,
        config.SOIL_MOISTURE_MIN - 0.10, config.SOIL_MOISTURE_IDEAL + 0.15)

    # --- Smoke dispersal sub-score ---
    smoke_score = _range_score(mix_h,
        config.MIXING_HEIGHT_MIN_FT, config.MIXING_HEIGHT_MAX_FT,
        0, config.MIXING_HEIGHT_MAX_FT + 5000)

    # --- Frontal passage sub-score (binary from check result) ---
    # frontal check returns False when NO shift detected (which is good)
    frontal_result = condition_results.get("frontal", (False, ""))
    frontal_score = 50 if frontal_result[0] else 100

    # --- Weighted average ---
    weights = {
        "wind": 0.25,
        "humidity": 0.20,
        "temperature": 0.15,
        "soil": 0.15,
        "smoke": 0.15,
        "frontal": 0.10,
    }
    weighted = (
        wind_score * weights["wind"]
        + humidity_score * weights["humidity"]
        + temp_score * weights["temperature"]
        + soil_score * weights["soil"]
        + smoke_score * weights["smoke"]
        + frontal_score * weights["frontal"]
    )

    # Red flag warning tanks the score
    if condition_red_flag[0] == "fail":
        weighted = min(weighted, 15)

    return round(max(0, min(100, weighted)))


def check_red_flag(lat, lon):
    url = f"https://api.weather.gov/alerts/active?point={lat},{lon}"
    headers = {"User-Agent": "ControlledBurnApp/1.0"}

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        alerts = response.json().get("features", [])

        for alert in alerts:
            props = alert.get("properties", {})
            event = props.get("event", "")
            if "Red Flag" in event or "Fire Weather" in event:
                headline = props.get("headline", "Red Flag Warning in effect.")
                return "fail", "fail", f"🚨 {headline}"

        return "ok", "ok", "No active Red Flag or Fire Weather warnings."

    except requests.exceptions.RequestException as e:
        return "caution", "caution", f"Could not retrieve NWS alerts: {e}"
        