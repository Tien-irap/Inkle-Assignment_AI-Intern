from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.places_model import PlacesRequest, PlacesResponse
from app.services.Places_service import PlacesService
from app.repos.places_repo import PlacesRepository
from app.core.db_connection import get_db

router = APIRouter()

def get_places_repo(db: AsyncIOMotorDatabase = Depends(get_db)) -> PlacesRepository:
    return PlacesRepository(db)

def get_places_service(repo: PlacesRepository = Depends(get_places_repo)) -> PlacesService:
    return PlacesService(repo)

@router.post("/places", response_model=PlacesResponse)
async def get_places_endpoint(
    request: PlacesRequest, 
    service: PlacesService = Depends(get_places_service)
):
    return await service.get_places(request.lat, request.lon)