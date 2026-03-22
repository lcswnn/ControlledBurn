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

# ── Nature-themed styling ─────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Merriweather:wght@400;700&family=Source+Sans+Pro:wght@400;600&display=swap');

    /* ── Layout ────────────────────────────────────────────────────────────── */
    .block-container {
        max-width: 1100px;
        padding-left: 2rem;
        padding-right: 2rem;
    }

    /* ── Background & base text ────────────────────────────────────────────── */
    .stApp {
        background: linear-gradient(175deg, #1a2e1a 0%, #1e2d1e 40%, #26332a 100%);
    }
    .stApp, .stApp p, .stApp li, .stApp span, .stApp label {
        color: #d4cdb8 !important;
        font-family: 'Source Sans Pro', sans-serif !important;
    }

    /* ── Headings ──────────────────────────────────────────────────────────── */
    .stApp h1 {
        font-family: 'Merriweather', serif !important;
        color: #c8b96e !important;
        text-shadow: 0 1px 3px rgba(0,0,0,0.4);
    }
    .stApp h2, .stApp h3 {
        font-family: 'Merriweather', serif !important;
        color: #a8bf8a !important;
    }

    /* ── Dividers ──────────────────────────────────────────────────────────── */
    .stApp hr {
        border-color: #3d5a3d !important;
        opacity: 0.6;
    }

    /* ── Input fields ──────────────────────────────────────────────────────── */
    .stTextInput > div > div > input {
        background-color: #2a3b2a !important;
        border: 1px solid #4a6b4a !important;
        color: #d4cdb8 !important;
        border-radius: 8px;
    }
    .stTextInput > div > div > input:focus {
        border-color: #7a9f5a !important;
        box-shadow: 0 0 6px rgba(122, 159, 90, 0.3);
    }

    /* ── Slider ────────────────────────────────────────────────────────────── */
    .stSlider > div > div > div > div {
        background-color: #4a6b4a !important;
    }
    .stSlider [role="slider"] {
        background-color: #7a9f5a !important;
    }

    /* ── Primary button ────────────────────────────────────────────────────── */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #5a7d3a, #4a6b2e) !important;
        color: #f0ead6 !important;
        border: 1px solid #6b8f4a !important;
        border-radius: 8px;
        font-family: 'Source Sans Pro', sans-serif !important;
        font-weight: 600 !important;
        letter-spacing: 0.3px;
        transition: all 0.2s ease;
    }
    .stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, #6b8f4a, #5a7d3a) !important;
        box-shadow: 0 2px 8px rgba(90, 125, 58, 0.4);
        transform: translateY(-1px);
    }

    /* ── Alert boxes (success / warning / error / info) ────────────────────── */
    .stAlert [data-testid="stNotificationContentSuccess"] {
        background-color: rgba(58, 107, 58, 0.25) !important;
        border-left: 4px solid #5a8f3a !important;
        color: #b8d4a0 !important;
    }
    .stAlert [data-testid="stNotificationContentWarning"] {
        background-color: rgba(140, 120, 50, 0.2) !important;
        border-left: 4px solid #b8a040 !important;
        color: #d4c87a !important;
    }
    .stAlert [data-testid="stNotificationContentError"] {
        background-color: rgba(140, 55, 45, 0.2) !important;
        border-left: 4px solid #a84032 !important;
        color: #d4a098 !important;
    }
    .stAlert [data-testid="stNotificationContentInfo"] {
        background-color: rgba(60, 90, 110, 0.2) !important;
        border-left: 4px solid #5a8faf !important;
        color: #a0c4d4 !important;
    }

    /* ── Metric cards ──────────────────────────────────────────────────────── */
    [data-testid="stMetric"] {
        background-color: rgba(42, 59, 42, 0.6);
        border: 1px solid #3d5a3d;
        border-radius: 8px;
        padding: 0.75rem;
    }
    [data-testid="stMetricLabel"] {
        color: #8fa87a !important;
    }
    [data-testid="stMetricValue"] {
        color: #e0d9c4 !important;
        font-family: 'Source Sans Pro', sans-serif !important;
    }

    /* ── Expander ──────────────────────────────────────────────────────────── */
    .streamlit-expanderHeader {
        background-color: rgba(42, 59, 42, 0.4) !important;
        border-radius: 8px;
        color: #a8bf8a !important;
        font-family: 'Source Sans Pro', sans-serif !important;
    }
    .streamlit-expanderContent {
        background-color: rgba(30, 45, 30, 0.3) !important;
        border: 1px solid #3d5a3d;
        border-radius: 0 0 8px 8px;
    }

    /* ── Caption ───────────────────────────────────────────────────────────── */
    .stCaption, [data-testid="stCaptionContainer"] {
        color: #8a8470 !important;
    }

    /* ── Scrollbar ─────────────────────────────────────────────────────────── */
    ::-webkit-scrollbar { width: 8px; }
    ::-webkit-scrollbar-track { background: #1a2e1a; }
    ::-webkit-scrollbar-thumb { background: #4a6b4a; border-radius: 4px; }
    ::-webkit-scrollbar-thumb:hover { background: #5a7d3a; }
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