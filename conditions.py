# Threshold logic, returns pass/fail per condition

def check_condition_1(weather_data):
    # Example condition: temperature below threshold
    if weather_data['temperature'] < config.TEMP_THRESHOLD:
        return "pass"
    else:
        return "fail"

def check_condition_2(weather_data):
    # Example condition: humidity above threshold
    if weather_data['humidity'] > config.HUMIDITY_THRESHOLD:
        return "pass"
    else:
        return "fail"

# Add more condition functions as needed