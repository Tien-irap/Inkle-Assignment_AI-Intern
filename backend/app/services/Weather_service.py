import httpx
from app.repos.weather_repo import WeatherRepository
from app.models.weather_model import WeatherResponse, DailyForecast
import logging
from app.core.logger import logs
from datetime import datetime, date

class WeatherService:
    def __init__(self, repo: WeatherRepository):
        self.repo = repo
        self.base_url = "https://api.open-meteo.com/v1/forecast"

    async def get_weather(self, lat: float, lon: float) -> WeatherResponse:
        # 1. Check Cache
        rounded_lat = round(lat, 2)
        rounded_lon = round(lon, 2)
        logs.log(logging.INFO, f"Checking cache for weather at {rounded_lat}, {rounded_lon}")
        
        cached = await self.repo.get_valid_cache(lat, lon)
        if cached:
            logs.log(logging.INFO, f"✓ Weather cache HIT for {rounded_lat}, {rounded_lon} (valid until {cached.get('timestamp')})")
            data = cached["data"]
            
            # Reconstruct DailyForecast objects from cached data
            daily_forecast = None
            if "daily_forecast" in data:
                daily_forecast = [
                    DailyForecast(
                        date=datetime.fromisoformat(d["date"]).date() if isinstance(d["date"], str) else d["date"],
                        max_temp=d["max_temp"],
                        min_temp=d["min_temp"],
                        condition=d["condition"],
                        rain_probability=d["rain_probability"]
                    )
                    for d in data["daily_forecast"]
                ]
            
            return WeatherResponse(
                temperature=data["temperature"],
                condition=data["condition"],
                feels_like=data.get("feels_like"),
                humidity=data.get("humidity"),
                wind_speed=data.get("wind_speed"),
                rain_probability=data.get("rain_probability"),
                pressure=data.get("pressure"),
                uv_index=data.get("uv_index"),
                daily_forecast=daily_forecast,
                source="cache"
            )

        # 2. Call External API (Open-Meteo)
        logs.log(logging.INFO, f"✗ Weather cache MISS for {rounded_lat}, {rounded_lon}. Calling Open-Meteo API...")
        async with httpx.AsyncClient() as client:
            try:
                params = {
                    "latitude": lat,
                    "longitude": lon,
                    "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation_probability,weather_code,surface_pressure,wind_speed_10m",
                    "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,weather_code",
                    "timezone": "auto",
                    "forecast_days": 7
                }
                resp = await client.get(self.base_url, params=params, timeout=10.0)
                resp.raise_for_status()
                raw_data = resp.json()
                
                # 3. Process Current Weather Data
                current = raw_data["current"]
                temp = current["temperature_2m"]
                code = current["weather_code"]
                condition = self._get_condition_text(code)
                feels_like = current.get("apparent_temperature")
                humidity = current.get("relative_humidity_2m")
                wind_speed = current.get("wind_speed_10m")
                rain_prob = current.get("precipitation_probability", 0)
                pressure = current.get("surface_pressure")
                
                # 4. Process Daily Forecast
                daily = raw_data.get("daily", {})
                daily_forecast = []
                
                if daily:
                    dates = daily.get("time", [])
                    max_temps = daily.get("temperature_2m_max", [])
                    min_temps = daily.get("temperature_2m_min", [])
                    weather_codes = daily.get("weather_code", [])
                    rain_probs = daily.get("precipitation_probability_max", [])
                    
                    for i in range(min(7, len(dates))):
                        forecast_date = datetime.fromisoformat(dates[i]).date()
                        daily_forecast.append(
                            DailyForecast(
                                date=forecast_date,
                                max_temp=max_temps[i],
                                min_temp=min_temps[i],
                                condition=self._get_condition_text(weather_codes[i]),
                                rain_probability=int(rain_probs[i]) if i < len(rain_probs) else 0
                            )
                        )
                
                # 5. Prepare data for caching
                weather_data = {
                    "temperature": temp,
                    "condition": condition,
                    "feels_like": feels_like,
                    "humidity": humidity,
                    "wind_speed": wind_speed,
                    "rain_probability": rain_prob,
                    "pressure": pressure,
                    "daily_forecast": [
                        {
                            "date": f.date.isoformat(),
                            "max_temp": f.max_temp,
                            "min_temp": f.min_temp,
                            "condition": f.condition,
                            "rain_probability": f.rain_probability
                        }
                        for f in daily_forecast
                    ]
                }

                # 6. Save to Cache
                await self.repo.save_cache(lat, lon, weather_data)

                return WeatherResponse(
                    temperature=temp,
                    condition=condition,
                    feels_like=feels_like,
                    humidity=humidity,
                    wind_speed=wind_speed,
                    rain_probability=rain_prob,
                    pressure=pressure,
                    daily_forecast=daily_forecast,
                    source="api"
                )

            except Exception as e:
                logs.log(logging.ERROR, f"Weather API failed: {str(e)}")
                # Fallback
                return WeatherResponse(
                    temperature=0.0,
                    condition="Unknown (API Error)",
                    source="error"
                )

    def _get_condition_text(self, code: int) -> str:
        """Maps WMO codes to human readable text."""
        # Source: Open-Meteo WMO Code documentation
        if code == 0: return "Clear sky"
        if code in [1, 2, 3]: return "Mainly clear, partly cloudy"
        if code in [45, 48]: return "Fog"
        if code in [51, 53, 55]: return "Drizzle"
        if code in [61, 63, 65]: return "Rain"
        if code in [71, 73, 75]: return "Snow fall"
        if code in [95, 96, 99]: return "Thunderstorm"
        return "Overcast"