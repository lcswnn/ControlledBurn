# conditions.py — threshold logic for controlled-burn checks
# Every public check returns (value, severity, message)
#   value   : bool (True = pass, False = fail)
#   severity: "ok" | "caution" | "fail"
#   message : human-readable explanation

import config


# ── helpers ───────────────────────────────────────────────────────────────────

def _range_score(value, ideal_low, ideal_high, fail_low, fail_high):
    """Map *value* to 0-100 based on ideal and failure boundaries."""
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


# ── individual checks ─────────────────────────────────────────────────────────

def check_wind(wind_speed_mph, wind_gust_mph, wind_direction_deg,
               prev_wind_direction_deg):

    # Hard fails
    if wind_speed_mph < config.WIND_SPEED_MIN_MPH:
        return False, "fail", "Wind speed is too low for a controlled burn."

    if wind_speed_mph > config.WIND_SPEED_MAX_MPH:
        return False, "fail", "Wind speed is too high for a controlled burn."

    gust_ratio = wind_gust_mph / max(wind_speed_mph, 0.1)
    if gust_ratio > config.WIND_GUST_MAX_RATIO:
        return False, "fail", "Wind gusts are too strong relative to sustained wind speed."

    if prev_wind_direction_deg is not None:
        shift = abs(wind_direction_deg - prev_wind_direction_deg)
        shift = min(shift, 360 - shift)
        if shift > config.WIND_DIRECTION_SHIFT_MAX_DEG:
            return False, "fail", "Wind direction has shifted too much recently."

    # Caution: approaching upper wind limit or gusty
    if wind_speed_mph > config.WIND_SPEED_MAX_MPH - 2:
        return True, "caution", (
            f"Wind speed {wind_speed_mph} mph is near the upper limit "
            f"({config.WIND_SPEED_MAX_MPH} mph)."
        )
    if gust_ratio > config.WIND_GUST_MAX_RATIO * 0.8:
        return True, "caution", (
            f"Gust ratio ({gust_ratio:.1f}×) is approaching the limit "
            f"({config.WIND_GUST_MAX_RATIO}×)."
        )

    return True, "ok", "Wind conditions are acceptable for a controlled burn."


def check_humidity(relative_humidity, fuel_height_ft):
    if fuel_height_ft <= config.FUEL_HEIGHT_SHORT_THRESHOLD_FT:
        rh_min = config.RH_MIN_SHORT_FUEL
        rh_max = config.RH_MAX_SHORT_FUEL
        label = "short"
    else:
        rh_min = config.RH_MIN_TALL_FUEL
        rh_max = config.RH_MAX_TALL_FUEL
        label = "tall"

    # Hard fails
    if relative_humidity < rh_min:
        return False, "fail", (
            f"Humidity {relative_humidity}% is too low for {label} fuel "
            f"(min {rh_min}%)."
        )
    if relative_humidity > rh_max:
        return False, "fail", (
            f"Humidity {relative_humidity}% is too high for {label} fuel "
            f"(max {rh_max}%)."
        )

    # Caution: within 5 % of either boundary
    if relative_humidity < rh_min + 5:
        return True, "caution", (
            f"Humidity {relative_humidity}% is near the low end for {label} fuel "
            f"(min {rh_min}%)."
        )
    if relative_humidity > rh_max - 5:
        return True, "caution", (
            f"Humidity {relative_humidity}% is near the high end for {label} fuel "
            f"(max {rh_max}%)."
        )

    return True, "ok", "Humidity is acceptable for current fuel conditions."


def check_temp(temperature_f, fuel_height_ft):
    if fuel_height_ft <= config.FUEL_HEIGHT_SHORT_THRESHOLD_FT:
        temp_min = config.TEMP_MIN_SHORT_FUEL_F
        temp_max = config.TEMP_MAX_SHORT_FUEL_F
        label = "short"
    else:
        temp_min = config.TEMP_MIN_TALL_FUEL_F
        temp_max = config.TEMP_MAX_TALL_FUEL_F
        label = "tall"

    # Hard fails
    if temperature_f < temp_min:
        return False, "fail", (
            f"Temperature {temperature_f}°F is too low for {label} fuel "
            f"(min {temp_min}°F)."
        )
    if temperature_f > temp_max:
        return False, "fail", (
            f"Temperature {temperature_f}°F is too high for {label} fuel "
            f"(max {temp_max}°F)."
        )

    # Caution: within 5°F of either boundary
    if temperature_f < temp_min + 5:
        return True, "caution", (
            f"Temperature {temperature_f}°F is near the low end for {label} fuel "
            f"(min {temp_min}°F)."
        )
    if temperature_f > temp_max - 5:
        return True, "caution", (
            f"Temperature {temperature_f}°F is near the high end for {label} fuel "
            f"(max {temp_max}°F)."
        )

    return True, "ok", "Temperature conditions are acceptable for a controlled burn."


def check_soil(soil_moisture_0_to_1cm, soil_moisture_1_to_3cm,
               soil_moisture_3_to_9cm, soil_moisture_9_to_27cm,
               soil_moisture_27_to_81cm):
    layers = [
        (soil_moisture_0_to_1cm,  "Surface (0–1 cm)"),
        (soil_moisture_1_to_3cm,  "Shallow (1–3 cm)"),
        (soil_moisture_3_to_9cm,  "Mid (3–9 cm)"),
        (soil_moisture_9_to_27cm, "Deep (9–27 cm)"),
        (soil_moisture_27_to_81cm, "Deep (27–81 cm)"),
    ]

    caution_msgs = []

    for value, label in layers:
        if value is None:
            continue
        if value < config.SOIL_MOISTURE_MIN:
            return False, "fail", f"{label} soil moisture is too low for a controlled burn."
        if value > config.SOIL_MOISTURE_IDEAL:
            return False, "fail", f"{label} soil moisture is too high for a controlled burn."

        # Near-boundary caution (within 15 % of the range edges)
        margin = (config.SOIL_MOISTURE_IDEAL - config.SOIL_MOISTURE_MIN) * 0.15
        if value < config.SOIL_MOISTURE_MIN + margin:
            caution_msgs.append(f"{label} moisture is on the dry side")
        elif value > config.SOIL_MOISTURE_IDEAL - margin:
            caution_msgs.append(f"{label} moisture is on the wet side")

    if caution_msgs:
        return True, "caution", "; ".join(caution_msgs) + "."

    return True, "ok", "Soil moisture is acceptable for a controlled burn."


def check_smoke_dispersal(mixing_height_ft, transport_wind_mph):
    # Hard fails
    if mixing_height_ft < config.MIXING_HEIGHT_MIN_FT:
        return False, "fail", "Mixing height is too low for good smoke dispersal."
    if mixing_height_ft > config.MIXING_HEIGHT_MAX_FT:
        return False, "fail", "Mixing height is unusually high — check for data accuracy."
    if transport_wind_mph < config.TRANSPORT_WIND_MIN_MPH:
        return False, "fail", "Transport wind speed is too low for effective smoke dispersal."
    if transport_wind_mph > config.TRANSPORT_WIND_MAX_MPH:
        return False, "fail", "Transport wind speed is too high — may cause smoke to spread too rapidly."

    # Caution: mixing height near minimum
    if mixing_height_ft < config.MIXING_HEIGHT_MIN_FT * 1.2:
        return True, "caution", (
            f"Mixing height ({mixing_height_ft:.0f} ft) is marginal for smoke dispersal."
        )

    return True, "ok", "Smoke dispersal conditions are acceptable for a controlled burn."


def check_frontal_passage(hourly_wind_directions):
    if len(hourly_wind_directions) < config.FRONTAL_PASSAGE_WINDOW_HRS:
        return False, "caution", "Not enough hourly wind direction data to assess frontal passage."

    initial_direction = hourly_wind_directions[0]
    for i in range(1, len(hourly_wind_directions)):
        shift = abs(hourly_wind_directions[i] - initial_direction)
        shift = min(shift, 360 - shift)
        if shift > config.WIND_DIRECTION_SHIFT_MAX_DEG:
            return False, "fail", (
                f"Significant wind shift detected ~{i} hrs from now — "
                "possible frontal passage."
            )

    return True, "ok", "No significant wind direction shift detected in the next 12 hours."


def check_6040_rule(temperature_f, relative_humidity, wind_speed_mph):
    temp_ok = temperature_f <= config.RULE_6040_TEMP_MAX_F
    rh_ok   = relative_humidity >= config.RULE_6040_RH_MIN_PCT
    wind_ok = config.WIND_SPEED_MIN_MPH <= wind_speed_mph <= config.WIND_SPEED_MAX_MPH

    if temp_ok and rh_ok and wind_ok:
        return True, "ok", "60/40 rule satisfied — conservative conditions met."

    reasons = []
    if not temp_ok:
        reasons.append(f"temp {temperature_f}°F exceeds 60°F")
    if not rh_ok:
        reasons.append(f"humidity {relative_humidity}% is below 40%")
    if not wind_ok:
        reasons.append(f"wind {wind_speed_mph} mph outside 5–15 mph range")

    return False, "caution", (
        f"60/40 rule NOT met: {', '.join(reasons)}. Proceed with extra caution."
    )


def check_aqi(aqi_value):
    """Check Air Quality Index for controlled burn suitability.

    US EPA AQI scale:
      0-50   Good               → ok
      51-100 Moderate            → caution
      101-150 Unhealthy for SG   → fail
      151+   Unhealthy or worse  → fail
    """
    if aqi_value is None:
        return True, "caution", "AQI data unavailable — check local air quality before burning."

    if aqi_value <= config.AQI_GOOD_MAX:
        return True, "ok", f"Air quality is good (AQI {aqi_value}) — safe to burn."

    if aqi_value <= config.AQI_MODERATE_MAX:
        return True, "caution", (
            f"Air quality is moderate (AQI {aqi_value}) — burning will add to "
            f"existing pollution. Monitor conditions."
        )

    if aqi_value <= config.AQI_USG_MAX:
        return False, "fail", (
            f"Air quality is unhealthy for sensitive groups (AQI {aqi_value}) — "
            f"do not burn."
        )

    return False, "fail", (
        f"Air quality is unhealthy (AQI {aqi_value}) — burning is not safe."
    )


# ── tiered verdict logic ──────────────────────────────────────────────────────
# Critical conditions: any single fail → hard fail verdict
# Secondary conditions: 1 fail → caution; 2+ fails → fail
# Score gate: < 50 → fail, < 75 → caution (even if individual checks pass)

CRITICAL_CONDITIONS = {"Red Flag Warning", "Wind", "Humidity", "Air Quality"}
SECONDARY_CONDITIONS = {"Temperature", "Soil Moisture", "Smoke Dispersal",
                        "Frontal Passage", "Precipitation"}


def determine_verdict(core_conditions, burn_score=None):
    """Return 'ok', 'caution', or 'fail' using tiered condition logic.

    Parameters
    ----------
    core_conditions : list of (label, (value, severity, message))
    burn_score : int or None — if provided, used as a secondary gate

    Returns
    -------
    str : 'ok' | 'caution' | 'fail'
    """
    critical_severities = []
    secondary_severities = []

    for label, cond in core_conditions:
        sev = cond[1]
        if label in CRITICAL_CONDITIONS:
            critical_severities.append(sev)
        else:
            secondary_severities.append(sev)

    # Any critical fail → hard fail
    if "fail" in critical_severities:
        return "fail"

    # Count secondary fails
    secondary_fails = secondary_severities.count("fail")

    # 2+ secondary fails → fail
    if secondary_fails >= 2:
        return "fail"

    # 1 secondary fail → caution
    if secondary_fails == 1:
        verdict = "caution"
    elif "caution" in critical_severities or "caution" in secondary_severities:
        verdict = "caution"
    else:
        verdict = "ok"

    # Score-based secondary gate
    if burn_score is not None:
        if burn_score < 50:
            return "fail"
        if burn_score < 75 and verdict == "ok":
            return "caution"

    return verdict


# ── composite burn score ──────────────────────────────────────────────────────

def calculate_burn_score(weather_data, fuel_height, condition_results,
                         condition_red_flag):
    # sourcery skip: merge-else-if-into-elif, swap-if-else-branches

    ws     = weather_data["wind_speed_mph"] or 0
    wg     = weather_data["wind_gusts_mph"] or 0
    rh     = weather_data["relative_humidity"] or 0
    temp   = weather_data["temperature_f"] or 0
    mix_h  = weather_data["mixing_height_ft"]
    sm     = weather_data["soil_moisture_0_to_1cm"]

    # --- Wind speed sub-score ---
    wind_score = _range_score(
        ws, config.WIND_SPEED_MIN_MPH, config.WIND_SPEED_MAX_MPH,
        0, config.WIND_SPEED_MAX_MPH + 10,
    )
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
    soil_score = _range_score(
        sm, config.SOIL_MOISTURE_MIN, config.SOIL_MOISTURE_IDEAL,
        config.SOIL_MOISTURE_MIN - 0.10, config.SOIL_MOISTURE_IDEAL + 0.15,
    )

    # --- Smoke dispersal sub-score ---
    smoke_score = _range_score(
        mix_h, config.MIXING_HEIGHT_MIN_FT, config.MIXING_HEIGHT_MAX_FT,
        0, config.MIXING_HEIGHT_MAX_FT + 5000,
    )

    # --- AQI sub-score ---
    aqi_val = weather_data.get("us_aqi")
    if aqi_val is not None:
        # 0-50 → 100, 51-100 → 70, 101-150 → 30, 151+ → 0
        if aqi_val <= config.AQI_GOOD_MAX:
            aqi_score = 100
        elif aqi_val <= config.AQI_MODERATE_MAX:
            aqi_score = max(0, 100 - (aqi_val - config.AQI_GOOD_MAX) * 0.6)
        else:
            aqi_score = max(0, 50 - (aqi_val - config.AQI_MODERATE_MAX) * 0.5)
    else:
        aqi_score = 50  # unknown → neutral

    # --- Frontal passage sub-score (binary from check result) ---
    frontal_result = condition_results.get("frontal", (False, "ok", ""))
    frontal_score = 50 if frontal_result[1] == "fail" else 100

    # --- Weighted average (reflects real-world burn priorities) ---
    # Wind + humidity are the primary fire behavior drivers (~55%)
    # AQI/smoke are increasingly regulated gating factors (~15%)
    # Frontal passage is a safety concern (~12%)
    # Temperature and soil are secondary (~18%)
    weights = {
        "wind": 0.30, "humidity": 0.25, "aqi": 0.15,
        "frontal": 0.12, "temperature": 0.10, "soil": 0.08,
    }
    # --- Combined AQI + smoke dispersal sub-score ---
    # Both relate to air quality / smoke management — average them
    combined_aqi_smoke = (aqi_score + smoke_score) / 2

    weighted = (
        wind_score         * weights["wind"]
        + humidity_score   * weights["humidity"]
        + temp_score       * weights["temperature"]
        + soil_score       * weights["soil"]
        + frontal_score    * weights["frontal"]
        + combined_aqi_smoke * weights["aqi"]
    )

    # Red flag warning tanks the score
    if condition_red_flag[1] == "fail":
        weighted = min(weighted, 15)

    return round(max(0, min(100, weighted)))