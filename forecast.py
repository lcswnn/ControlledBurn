# forecast.py — evaluate weekly forecast data for controlled-burn suitability
# Runs the same condition checks from conditions.py against each forecast day
# and produces a scored summary with a best-day recommendation.

from datetime import datetime, timedelta
import conditions


def evaluate_day(day_data, fuel_height):
    """Run all condition checks against a single forecast day's data.

    Parameters
    ----------
    day_data : dict   – one element from weather.get_weekly_forecast()
    fuel_height : float

    Returns
    -------
    dict with keys:
        date, day_label, checks (list of (label, severity, message)),
        verdict ("ok" | "caution" | "fail"), score (0-100), summary
    """

    # Wind — forecast gives daily max, so we use it as a conservative estimate.
    # Gusts are also daily max.  No previous-hour direction for forecast days,
    # so we pass None for the shift check (it'll be skipped inside check_wind).
    wind_speed = day_data.get("wind_speed_mph") or 0
    wind_gusts = day_data.get("wind_gusts_mph") or wind_speed
    wind_dir = day_data.get("wind_direction_deg")

    cond_wind = conditions.check_wind(
        wind_speed, wind_gusts, wind_dir or 0, None
    )

    # Humidity — use mean RH for the day
    rh = day_data.get("relative_humidity") or 0
    cond_humidity = conditions.check_humidity(rh, fuel_height)

    # Temperature — use the average of min/max as representative
    temp = day_data.get("temperature_f") or 0
    cond_temp = conditions.check_temp(temp, fuel_height)

    # Soil moisture
    cond_soil = conditions.check_soil(
        day_data.get("soil_moisture_0_to_1cm"),
        day_data.get("soil_moisture_1_to_3cm"),
        day_data.get("soil_moisture_3_to_9cm"),
        day_data.get("soil_moisture_9_to_27cm"),
        day_data.get("soil_moisture_27_to_81cm"),
    )

    # Smoke dispersal — use mixing height + wind speed as transport proxy
    mixing = day_data.get("mixing_height_ft")
    if mixing is not None:
        cond_smoke = conditions.check_smoke_dispersal(mixing, wind_speed)
    else:
        cond_smoke = (True, "caution", "Mixing height data unavailable for this day.")

    # Frontal passage — check hourly wind dirs for that day
    hourly_dirs = day_data.get("hourly_wind_directions", [])
    cond_frontal = conditions.check_frontal_passage(hourly_dirs)

    # 60/40 rule (advisory)
    cond_6040 = conditions.check_6040_rule(temp, rh, wind_speed)

    # AQI check
    aqi_val = day_data.get("us_aqi")
    cond_aqi = conditions.check_aqi(aqi_val)

    # Precipitation penalty — not a hard conditions.py check, but useful
    precip = day_data.get("precipitation_in") or 0
    precip_prob = day_data.get("precipitation_probability") or 0
    if precip > 0.25 or precip_prob > 60:
        cond_precip = (False, "fail",
                       f"Rain expected ({precip:.2f}\" forecast, {precip_prob}% prob).")
    elif precip > 0.05 or precip_prob > 30:
        cond_precip = (True, "caution",
                       f"Light rain possible ({precip:.2f}\" forecast, {precip_prob}% prob).")
    else:
        cond_precip = (True, "ok", "No significant precipitation expected.")

    checks = [
        ("Wind", cond_wind),
        ("Humidity", cond_humidity),
        ("Temperature", cond_temp),
        ("Soil Moisture", cond_soil),
        ("Smoke Dispersal", cond_smoke),
        ("Frontal Passage", cond_frontal),
        ("Air Quality", cond_aqi),
        ("Precipitation", cond_precip),
    ]

    # ── Weighted score (mirrors real-world burn priorities) ───────────────
    # Critical checks get heavier deductions than secondary ones
    CRITICAL_DEDUCTIONS = {"Wind": 25, "Humidity": 22, "Air Quality": 18}
    SECONDARY_DEDUCTIONS = {"Temperature": 10, "Soil Moisture": 8,
                            "Smoke Dispersal": 10, "Frontal Passage": 12,
                            "Precipitation": 12}

    score = 100
    for label, (_, sev, _) in checks:
        if sev == "fail":
            score -= CRITICAL_DEDUCTIONS.get(label,
                     SECONDARY_DEDUCTIONS.get(label, 15))
        elif sev == "caution":
            # Caution deductions are ~40% of fail deductions
            fail_deduct = CRITICAL_DEDUCTIONS.get(label,
                          SECONDARY_DEDUCTIONS.get(label, 15))
            score -= round(fail_deduct * 0.4)

    # Rain probability penalty
    if precip_prob > 50:
        score -= 8
    elif precip_prob > 25:
        score -= 4
    score = max(0, min(100, score))

    # ── Tiered verdict (same logic as current-day assessment) ─────────────
    verdict = conditions.determine_verdict(checks, score)

    # Parse date for display
    try:
        dt = datetime.strptime(day_data["date"], "%Y-%m-%d")
        day_label = dt.strftime("%a %m/%d")
    except (ValueError, KeyError):
        day_label = day_data.get("date", "Unknown")

    return {
        "date": day_data.get("date"),
        "day_label": day_label,
        "checks": checks,
        "verdict": verdict,
        "score": score,
        "advisory_6040": cond_6040,
        "temperature_f": temp,
        "wind_speed_mph": wind_speed,
        "wind_gusts_mph": wind_gusts,
        "relative_humidity": rh,
        "precipitation_in": precip,
        "precipitation_probability": precip_prob,
        "mixing_height_ft": mixing,
        "us_aqi": aqi_val,
    }


def evaluate_week(weekly_data, fuel_height):
    """Score every day in the weekly forecast.

    Returns
    -------
    list[dict] — one evaluate_day result per day, sorted by date
    """
    results = [evaluate_day(d, fuel_height) for d in weekly_data]
    results.sort(key=lambda r: r["date"])
    return results


def best_burn_days(weekly_results, top_n=3):
    """Return up to `top_n` days ranked by score (highest first),
    excluding any day with verdict == 'fail'."""
    candidates = [r for r in weekly_results if r["verdict"] != "fail"]
    candidates.sort(key=lambda r: r["score"], reverse=True)
    return candidates[:top_n]


# ── Optimal Burn Window Finder ────────────────────────────────────────────────

def find_optimal_windows(weekly_results, min_consecutive=1):
    """Find optimal burn windows — consecutive days with verdict != 'fail'.

    Identifies streaks of favorable days and ranks them by average score.

    Parameters
    ----------
    weekly_results : list[dict] — output of evaluate_week()
    min_consecutive : int — minimum consecutive favorable days to form a window

    Returns
    -------
    list[dict] with keys:
        start_date, end_date, start_label, end_label, days (int),
        avg_score, min_score, verdicts (list[str]), day_details (list[dict])
    """
    if not weekly_results:
        return []

    # Sort by date
    sorted_days = sorted(weekly_results, key=lambda r: r["date"])

    # Find consecutive non-fail streaks
    windows = []
    current_streak = []

    for day in sorted_days:
        if day["verdict"] != "fail":
            current_streak.append(day)
        else:
            if len(current_streak) >= min_consecutive:
                windows.append(current_streak)
            current_streak = []

    # Don't forget last streak
    if len(current_streak) >= min_consecutive:
        windows.append(current_streak)

    # Build window summaries
    results = []
    for streak in windows:
        scores = [d["score"] for d in streak]
        results.append({
            "start_date": streak[0]["date"],
            "end_date": streak[-1]["date"],
            "start_label": streak[0]["day_label"],
            "end_label": streak[-1]["day_label"],
            "days": len(streak),
            "avg_score": round(sum(scores) / len(scores), 1),
            "min_score": min(scores),
            "max_score": max(scores),
            "verdicts": [d["verdict"] for d in streak],
            "day_details": streak,
        })

    # Sort by avg_score descending (best windows first)
    results.sort(key=lambda w: w["avg_score"], reverse=True)
    return results


def format_window_summary(window):
    """Return a human-readable string for a burn window."""
    if window["days"] == 1:
        return (
            f"{window['start_label']} — Score: {window['avg_score']:.0f}/100"
        )
    return (
        f"{window['start_label']} → {window['end_label']} "
        f"({window['days']} days) — "
        f"Avg Score: {window['avg_score']:.0f}/100, "
        f"Range: {window['min_score']}–{window['max_score']}"
    )