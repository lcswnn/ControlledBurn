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

# ── Forest Park Forever–inspired styling ──────────────────────────────────────
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Lora:wght@400;600;700&family=Open+Sans:wght@400;600&display=swap');

    /* ── Layout ────────────────────────────────────────────────────────────── */
    .block-container {
        max-width: 1100px;
        padding-left: 2rem;
        padding-right: 2rem;
    }

    /* ── Background & base text ────────────────────────────────────────────── */
    .stApp {
        background-color: #faf9f5;
    }
    .stApp, .stApp p, .stApp li, .stApp span:not([data-testid="stIconMaterial"]), .stApp label,
    .stApp [data-testid="stMarkdownContainer"] {
        color: #3b3b3b !important;
        font-family: 'Open Sans', sans-serif !important;
    }

    /* ── Top accent bar ────────────────────────────────────────────────────── */
    .stApp::before {
        content: '';
        display: block;
        position: fixed;
        top: 0; left: 0; right: 0;
        height: 4px;
        background: linear-gradient(90deg, #4caf50, #f7941d, #4caf50);
        z-index: 9999;
    }

    /* ── Headings ──────────────────────────────────────────────────────────── */
    .stApp h1 {
        font-family: 'Lora', serif !important;
        color: #2e7d32 !important;
    }
    .stApp h2, .stApp h3 {
        font-family: 'Lora', serif !important;
        color: #3a7d34 !important;
    }

    /* ── Dividers ──────────────────────────────────────────────────────────── */
    .stApp hr {
        border-color: #c8dcc0 !important;
        opacity: 0.8;
    }

    /* ── Input fields ──────────────────────────────────────────────────────── */
    .stTextInput > div > div > input {
        background-color: #ffffff !important;
        border: 1px solid #b5cfb0 !important;
        color: #3b3b3b !important;
        border-radius: 8px;
    }
    .stTextInput > div > div > input:focus {
        border-color: #4caf50 !important;
        box-shadow: 0 0 6px rgba(76, 175, 80, 0.25);
    }

    /* ── Slider ────────────────────────────────────────────────────────────── */
    .stSlider > div > div > div > div {
        background-color: #a5d6a7 !important;
    }
    .stSlider [role="slider"] {
        background-color: #4caf50 !important;
    }

    /* ── Primary button (orange) ───────────────────────────────────────────── */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #f7941d, #e8850f) !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 8px;
        font-family: 'Open Sans', sans-serif !important;
        font-weight: 600 !important;
        letter-spacing: 0.3px;
        transition: all 0.2s ease;
        box-shadow: 0 2px 4px rgba(247, 148, 29, 0.3);
    }
    .stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, #e8850f, #d4770a) !important;
        box-shadow: 0 4px 12px rgba(247, 148, 29, 0.4);
        transform: translateY(-1px);
    }

    /* ── Alert boxes ───────────────────────────────────────────────────────── */
    /* Success — leafy green */
    [data-testid="stAlert"] [role="alert"]:has([data-testid="stNotificationContentSuccess"]) {
        background-color: #e8f5e9 !important;
        border-left: 4px solid #4caf50 !important;
    }
    [data-testid="stNotificationContentSuccess"],
    [data-testid="stNotificationContentSuccess"] p,
    [data-testid="stNotificationContentSuccess"] span {
        color: #2e5a2e !important;
    }
    /* Warning — orange */
    [data-testid="stAlert"] [role="alert"]:has([data-testid="stNotificationContentWarning"]) {
        background-color: #fff8e1 !important;
        border-left: 4px solid #f7941d !important;
    }
    [data-testid="stNotificationContentWarning"],
    [data-testid="stNotificationContentWarning"] p,
    [data-testid="stNotificationContentWarning"] span {
        color: #5a4520 !important;
    }
    /* Error — warm red */
    [data-testid="stAlert"] [role="alert"]:has([data-testid="stNotificationContentError"]) {
        background-color: #fce4e4 !important;
        border-left: 4px solid #d44a3a !important;
    }
    [data-testid="stNotificationContentError"],
    [data-testid="stNotificationContentError"] p,
    [data-testid="stNotificationContentError"] span {
        color: #5a2020 !important;
    }
    /* Info — sky blue */
    [data-testid="stAlert"] [role="alert"]:has([data-testid="stNotificationContentInfo"]) {
        background-color: #e3f2fd !important;
        border-left: 4px solid #42a5f5 !important;
    }
    [data-testid="stNotificationContentInfo"],
    [data-testid="stNotificationContentInfo"] p,
    [data-testid="stNotificationContentInfo"] span {
        color: #1a4a6e !important;
    }

    /* ── Metric cards ──────────────────────────────────────────────────────── */
    [data-testid="stMetric"] {
        background-color: #ffffff;
        border: 1px solid #dce8d6;
        border-radius: 8px;
        padding: 0.75rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    }
    [data-testid="stMetricLabel"] {
        color: #6a8f5e !important;
        font-weight: 600 !important;
    }
    [data-testid="stMetricValue"] {
        color: #2e7d32 !important;
        font-family: 'Open Sans', sans-serif !important;
        font-weight: 700 !important;
    }

    /* ── Expander — fixed arrow rendering ──────────────────────────────────── */
    [data-testid="stExpander"] {
        border: 1px solid #dce8d6 !important;
        border-radius: 8px !important;
        background-color: transparent !important;
    }
    [data-testid="stExpander"] summary {
        background-color: #f0f7ec !important;
        color: #3a7d34 !important;
        font-family: 'Open Sans', sans-serif !important;
        font-weight: 600 !important;
        padding: 0.6rem 1rem !important;
    }
    [data-testid="stExpander"] summary p,
    [data-testid="stExpander"] summary span {
        color: #3a7d34 !important;
    }
    /* Arrow icon fix — don't let global color/font rules break the SVG */
    [data-testid="stExpander"] summary svg {
        fill: currentColor !important;
        width: 1rem !important;
        height: 1rem !important;
        flex-shrink: 0 !important;
    }
    /* Preserve Material Icons font for expander arrow glyphs */
    [data-testid="stExpander"] summary span[data-testid="stIconMaterial"],
    [data-testid="stExpander"] summary .material-symbols-rounded,
    [data-testid="stExpander"] summary i {
        font-family: 'Material Symbols Rounded', sans-serif !important;
        font-size: 1.25rem !important;
        color: #3a7d34 !important;
    }
    [data-testid="stExpander"] [data-testid="stExpanderDetails"] {
        background-color: #fafcf8 !important;
        padding: 1rem !important;
    }

    /* ── Caption ───────────────────────────────────────────────────────────── */
    .stCaption, [data-testid="stCaptionContainer"] {
        color: #8a8a7a !important;
    }

    /* ── Spinner ───────────────────────────────────────────────────────────── */
    .stSpinner > div > div {
        border-top-color: #f7941d !important;
    }

    /* ── Scrollbar ─────────────────────────────────────────────────────────── */
    ::-webkit-scrollbar { width: 8px; }
    ::-webkit-scrollbar-track { background: #f5f5f0; }
    ::-webkit-scrollbar-thumb { background: #a5d6a7; border-radius: 4px; }
    ::-webkit-scrollbar-thumb:hover { background: #4caf50; }
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
        st.subheader(f"📍 {location}")
        st.markdown(
            f'<span style="display:inline-block; background:#e8f5e9; color:#2e7d32; '
            f'padding:0.25rem 0.75rem; border-radius:6px; font-size:0.85rem; '
            f'font-family:monospace; border:1px solid #c8e6c9;">'
            f'{lat:.4f}, {lon:.4f}</span>',
            unsafe_allow_html=True,
        )

        # Map centered on the location (light style)
        map_df = pd.DataFrame({"lat": [lat], "lon": [lon]})
        st.map(map_df, zoom=11, use_container_width=True,
               color="#d44a3a")

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