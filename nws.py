import requests

def check_red_flag(lat, lon):
    url = f"https://api.weather.gov/alerts/active?point={lat},{lon}"
    headers = {"User-Agent": "ControlledBurnApp/1.0 (your@email.com)"}

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