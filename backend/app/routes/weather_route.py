from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.weather_model import WeatherRequest, WeatherResponse
from app.services.Weather_service import WeatherService
from app.repos.weather_repo import WeatherRepository
from app.core.db_connection import get_db

router = APIRouter()

# --- Dependency Injection ---
def get_weather_repo(db: AsyncIOMotorDatabase = Depends(get_db)) -> WeatherRepository:
    return WeatherRepository(db)

def get_weather_service(repo: WeatherRepository = Depends(get_weather_repo)) -> WeatherService:
    return WeatherService(repo)

@router.post("/weather", response_model=WeatherResponse)
async def get_weather_endpoint(
    request: WeatherRequest, 
    service: WeatherService = Depends(get_weather_service)
):
    return await service.get_weather(request.lat, request.lon)