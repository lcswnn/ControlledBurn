import streamlit as st
import pandas as pd
import geocode
import weather
import conditions
import nws

st.set_page_config(
    page_title="Controlled Burn Checker",
    page_icon="🔥",
    layout="wide"
)

# ── Custom width constraint ───────────────────────────────────────────────────
st.markdown(
    """
    <style>
    .block-container {
        max-width: 1100px;
        padding-left: 2rem;
        padding-right: 2rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🔥 Controlled Burn Conditions Checker")
st.caption("Enter a location and fuel height to assess whether conditions are safe for a controlled burn.")

st.divider()

# ── Inputs (full width, above the two-column layout) ─────────────────────────
col_loc, col_fuel = st.columns([2, 1])
with col_loc:
    location = st.text_input("📍 Location", placeholder="e.g. Chicago, IL")
with col_fuel:
    fuel_height = st.slider("🌿 Fuel Height (ft)", min_value=0.5, max_value=8.0,
                            value=2.0, step=0.5)

run = st.button("Check Conditions", type="primary", use_container_width=True)

# ── Main logic ────────────────────────────────────────────────────────────────
if run and location:
    with st.spinner("Fetching weather data..."):
        try:
            lat, lon = geocode.geocode(location)
            weather_data = weather.get_weather(lat, lon)
        except Exception as e:
            st.error(f"Could not retrieve data for '{location}': {e}")
            st.stop()

    if weather_data is None:
        st.error("Weather data unavailable. Check your location and try again.")
        st.stop()

    # ── Run all condition checks ──────────────────────────────────────────────
    condition_wind = conditions.check_wind(
        weather_data["wind_speed_mph"],
        weather_data["wind_gusts_mph"],
        weather_data["wind_direction_deg"],
        weather_data["hourly_wind_directions"][0] if weather_data["hourly_wind_directions"] else None
    )
    condition_humidity = conditions.check_humidity(
        weather_data["relative_humidity"],
        fuel_height
    )
    condition_temp = conditions.check_temp(
        weather_data["temperature_f"],
        fuel_height
    )
    condition_soil = conditions.check_soil(
        weather_data["soil_moisture_0_to_1cm"],
        weather_data["soil_moisture_1_to_3cm"],
        weather_data["soil_moisture_3_to_9cm"],
        weather_data["soil_moisture_9_to_27cm"],
        weather_data["soil_moisture_27_to_81cm"]
    )
    condition_smoke = conditions.check_smoke_dispersal(
        weather_data["mixing_height_ft"],
        weather_data["wind_speed_mph"]
    )
    condition_frontal = conditions.check_frontal_passage(
        weather_data["hourly_wind_directions"]
    )
    condition_red_flag = nws.check_red_flag(lat, lon)
    condition_6040 = conditions.check_6040_rule(
        weather_data["temperature_f"],
        weather_data["relative_humidity"],
        weather_data["wind_speed_mph"]
    )

    core_conditions = [
        ("🚨 Red Flag Warning",  condition_red_flag),
        ("💨 Wind",              condition_wind),
        ("💧 Humidity",          condition_humidity),
        ("🌡 Temperature",       condition_temp),
        ("🌱 Soil Moisture",     condition_soil),
        ("☁️ Smoke Dispersal",   condition_smoke),
        ("🌬 Frontal Passage",   condition_frontal),
    ]

    # ── Determine verdict ─────────────────────────────────────────────────────
    severities = [c[1][1] for c in core_conditions]

    if "fail" in severities:
        verdict = "fail"
    elif "caution" in severities:
        verdict = "caution"
    else:
        verdict = "ok"

    st.divider()

    # ══════════════════════════════════════════════════════════════════════════
    # TWO-COLUMN RESULTS LAYOUT
    # ══════════════════════════════════════════════════════════════════════════
    left_col, right_col = st.columns([1, 1], gap="large")

    # ── LEFT COLUMN — Map + Verdict + Advisory ────────────────────────────────
    with left_col:
        st.subheader(f"📍 {location}  `{lat:.4f}, {lon:.4f}`")

        # Map centered on the location
        map_df = pd.DataFrame({"lat": [lat], "lon": [lon]})
        st.map(map_df, zoom=11, use_container_width=True)

        # Verdict banner
        st.subheader("📋 Verdict")
        if verdict == "ok":
            st.success("✅ BURN APPROVED — All conditions are met.")
        elif verdict == "caution":
            st.warning("⚠️ PROCEED WITH CAUTION — Conditions are marginal.")
        else:
            st.error("❌ BURN NOT RECOMMENDED — One or more conditions failed.")

        # 60/40 advisory
        st.divider()
        st.subheader("📌 Advisory")
        if condition_6040[1] == "ok":
            st.info(f"**60/40 Rule** — {condition_6040[2]}")
        else:
            st.warning(f"**60/40 Rule (Advisory)** — {condition_6040[2]}")

    # ── RIGHT COLUMN — Weather + Breakdown + Expanders ────────────────────────
    with right_col:
        st.subheader("🌤 Weather Snapshot")
        c1, c2, c3 = st.columns(3)
        c1.metric("🌡 Temp", f"{weather_data['temperature_f']}°F")
        c2.metric("💨 Wind", f"{weather_data['wind_speed_mph']} mph")
        c3.metric("💧 Humidity", f"{weather_data['relative_humidity']}%")

        c4, c5 = st.columns(2)
        c4.metric("🌬 Gusts", f"{weather_data['wind_gusts_mph']} mph")
        c5.metric("☁️ Mixing Ht", f"{weather_data['mixing_height_ft']:.0f} ft")

        st.divider()

        # Condition breakdown
        st.subheader("🔍 Condition Breakdown")

        for label, cond in core_conditions:
            severity = cond[1]
            message = cond[2]
            if severity == "ok":
                st.success(f"**{label}** — {message}")
            elif severity == "caution":
                st.warning(f"**{label}** — {message}")
            else:
                st.error(f"**{label}** — {message}")

        # Soil detail expander
        with st.expander("🌱 Soil Moisture Detail"):
            s1, s2, s3 = st.columns(3)
            s1.metric("0–1 cm",  f"{weather_data['soil_moisture_0_to_1cm']:.3f}")
            s2.metric("1–3 cm",  f"{weather_data['soil_moisture_1_to_3cm']:.3f}")
            s3.metric("3–9 cm",  f"{weather_data['soil_moisture_3_to_9cm']:.3f}")

            s4, s5 = st.columns(2)
            s4.metric("9–27 cm",  f"{weather_data['soil_moisture_9_to_27cm']:.3f}")
            s5.metric("27–81 cm", f"{weather_data['soil_moisture_27_to_81cm']:.3f}")

        # Wind forecast expander
        with st.expander("💨 12-Hour Wind Direction Forecast"):
            dirs = weather_data["hourly_wind_directions"]
            if dirs:
                per_row = 6
                for row_start in range(0, len(dirs), per_row):
                    row_dirs = dirs[row_start:row_start + per_row]
                    cols = st.columns(per_row)
                    for j, (col, d) in enumerate(zip(cols, row_dirs)):
                        col.metric(f"+{row_start + j}h", f"{d}°")
            else:
                st.write("No hourly wind data available.")

elif run and not location:
    st.warning("Please enter a location before checking conditions.")