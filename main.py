import geocode
import weather
import conditions

def get_fuel_height():
    while True:
        try:
            height = float(input("Enter fuel/vegetation height in feet: "))
            if height <= 0:
                print("Height must be positive.")
                continue
            return height
        except ValueError:
            print("Invalid input. Enter a number.")

def main():
    while True:
        location = input("Enter location for controlled burn (or 'exit' to quit): ")
        if location.lower() == 'exit':
            break

        lat, lon = geocode.geocode(location)
        print(f"Coordinates for {location}: {lat}, {lon}")

        print(f"Fetching weather data for {location}...")
        weather_data = weather.get_weather(lat, lon)
        print(f"Weather data for {location}: {weather_data}")

        # Collect fuel height before running checks
        fuel_height = get_fuel_height()

        print("Completing checks...")

        # Wind
        condition_wind = conditions.check_wind(
            weather_data["wind_speed_mph"],
            weather_data["wind_gusts_mph"],
            weather_data["wind_direction_deg"],
            weather_data["hourly_wind_directions"][0] if weather_data["hourly_wind_directions"] else None
        )
        print(f"Current Wind: {weather_data['wind_speed_mph']} mph")
        print(f"Wind condition: {condition_wind[1]}")

        # Humidity — now uses fuel height to pick thresholds
        condition_humidity = conditions.check_humidity(
            weather_data["relative_humidity"],
            fuel_height
        )
        print(f"Current Relative Humidity: {weather_data['relative_humidity']}%")
        print(f"Fuel height: {fuel_height} ft")
        print(f"Humidity condition: {condition_humidity[1]}")

        # Temperature
        condition_temp = conditions.check_temp(weather_data["temperature_f"], fuel_height)
        print(f"Current Temperature: {weather_data['temperature_f']} °F")
        print(f"Temperature condition: {condition_temp[1]}")

        #60/40 rule
        condition_6040 = conditions.check_6040_rule(
            weather_data["temperature_f"],
            weather_data["relative_humidity"],
            weather_data["wind_speed_mph"]
        )
        print(f"60/40 Rule condition (Temp under 60, Relative humidity over 40%, wind @ 5-15 mph): {condition_6040[1]}")
        
        #soil
        condition_soil = conditions.check_soil(
            weather_data["soil_moisture_0_to_1cm"],
            weather_data["soil_moisture_1_to_3cm"],
            weather_data["soil_moisture_3_to_9cm"],
            weather_data["soil_moisture_9_to_27cm"],
            weather_data["soil_moisture_27_to_81cm"]
        )
        print(f"Soil moisture at 0-1cm: {weather_data['soil_moisture_0_to_1cm']}")
        print(f"Soil moisture at 1-3cm: {weather_data['soil_moisture_1_to_3cm']}")
        print(f"Soil moisture at 3-9cm: {weather_data['soil_moisture_3_to_9cm']}")
        print(f"Soil moisture condition: {condition_soil[1]}")
        
        #smoke
        condition_smoke = conditions.check_smoke_dispersal(
            weather_data["mixing_height_ft"],
            weather_data["wind_speed_mph"]
        )
        print(f"Mixing height: {weather_data['mixing_height_ft']:.1f} ft")
        print(f"Smoke dispersal condition: {condition_smoke[1]}")
        
        #frontal passage
        condition_frontal = conditions.check_frontal_passage(
            weather_data["hourly_wind_directions"]
        )
        print(f"Frontal passage condition: {condition_frontal[1]}")
        
        #red flag conditions
        condition_red_flag = conditions.check_red_flag(lat, lon)
        print(f"Red flag conditions: {condition_red_flag}")
        
        
        # Aggregate all conditions into go/no-go
        all_conditions = [
            condition_wind,
            condition_humidity,
            condition_temp,
            condition_soil,
            condition_smoke,
            condition_frontal,
            condition_red_flag
        ]

        burn_approved = all(c[0] for c in all_conditions)

        # Calculate burn readiness score (0–100)
        condition_map = {
            "frontal": condition_frontal,
        }
        burn_score = conditions.calculate_burn_score(
            weather_data, fuel_height, condition_map, condition_red_flag
        )

        print("\n" + "="*45)
        print(f"Overall Burn Score: {burn_score}/100", end="  ")
        if burn_score >= 80:
            print("(Excellent)")
        elif burn_score >= 60:
            print("(Good)")
        elif burn_score >= 40:
            print("(Marginal)")
        elif burn_score >= 20:
            print("(Poor)")
        else:
            print("(Do Not Burn)")
        print("="*45)

        if not condition_6040[0]:
          print(f"⚠️  Advisory: {condition_6040[1]}")
        if condition_red_flag == True:
          print(f"⚠️  RED FLAG WARNING: {condition_red_flag[1]}")
        if burn_approved:
            print("✅ BURN APPROVED — All conditions are met.")
        else:
            print("❌ BURN NOT RECOMMENDED — Failed conditions:")
            for c in all_conditions:
                if not c[0]:
                    print(f"  • {c[1]}")
        print("="*45)
        break

if __name__ == "__main__":
    main()