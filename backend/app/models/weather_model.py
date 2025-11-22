from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date

class WeatherRequest(BaseModel):
    lat: float
    lon: float

class DailyForecast(BaseModel):
    date: date
    max_temp: float
    min_temp: float
    condition: str
    rain_probability: int  # Percentage

class WeatherResponse(BaseModel):
    temperature: float
    condition: str
    feels_like: Optional[float] = None
    humidity: Optional[int] = None
    wind_speed: Optional[float] = None
    rain_probability: Optional[int] = None  # Percentage
    pressure: Optional[float] = None
    uv_index: Optional[float] = None
    daily_forecast: Optional[List[DailyForecast]] = None
    source: str  # "cache" or "api"
    location_name: Optional[str] = None