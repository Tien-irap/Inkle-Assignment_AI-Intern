from pydantic import BaseModel
from typing import List, Optional

class Place(BaseModel):
    name: str
    category: str
    lat: float
    lon: float

class PlacesRequest(BaseModel):
    lat: float
    lon: float

class PlacesResponse(BaseModel):
    places: List[Place]
    source: str  # "cache" or "api"