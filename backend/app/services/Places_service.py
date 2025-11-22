import httpx
import logging
from app.repos.places_repo import PlacesRepository
from app.models.places_model import PlacesResponse, Place
from app.core.logger import logs
from app.core.llm_connection import llm_client

class PlacesService:
    def __init__(self, repo: PlacesRepository):
        self.repo = repo
        self.overpass_url = "https://overpass-api.de/api/interpreter"

    async def get_places(self, lat: float, lon: float, location_name: str = None) -> PlacesResponse:
        # 1. Check Cache
        rounded_lat = round(lat, 2)
        rounded_lon = round(lon, 2)
        logs.log(logging.INFO, f"Checking cache for places at {rounded_lat}, {rounded_lon}")
        
        cached = await self.repo.get_cached_places(lat, lon)
        if cached:
            logs.log(logging.INFO, f"✓ Places cache HIT for {rounded_lat}, {rounded_lon} (valid until {cached.get('timestamp')})")
            # Convert dictionary back to Pydantic models
            places_list = [Place(**p) for p in cached["places"]]
            return PlacesResponse(places=places_list, source="cache")

        # 2. Get places from Overpass API (nearby attractions)
        logs.log(logging.INFO, f"✗ Places cache MISS for {rounded_lat}, {rounded_lon}. Fetching from Overpass API...")
        
        overpass_places = await self._fetch_from_overpass(lat, lon)
        overpass_names = [p.name for p in overpass_places]
        
        # 3. Enhance with LLM suggestions (popular attractions)
        llm_places = []
        if location_name:
            logs.log(logging.INFO, f"Getting LLM suggestions for {location_name}")
            llm_suggestions = await llm_client.enhance_places_suggestions(location_name, overpass_names)
            
            # Convert LLM suggestions to Place objects (without coordinates)
            for name in llm_suggestions:
                if name not in overpass_names:  # Avoid duplicates
                    llm_places.append(Place(
                        name=name,
                        category="attraction",
                        lat=lat,  # Use city center coordinates
                        lon=lon
                    ))
        
        # 4. Combine and prioritize: Overpass places first (they have exact coords), then LLM
        combined_places = overpass_places + llm_places
        
        # 5. Cache combined results
        places_dicts = [p.dict() for p in combined_places[:50]]
        await self.repo.cache_places(lat, lon, places_dicts)
        
        logs.log(logging.INFO, f"Total places: {len(combined_places)} (Overpass: {len(overpass_places)}, LLM: {len(llm_places)})")
        
        return PlacesResponse(places=combined_places, source="api+llm")
    
    async def _fetch_from_overpass(self, lat: float, lon: float) -> list[Place]:
        """Fetch nearby places from Overpass API with smaller radius."""
        # Simplified Overpass query with smaller radius for speed
        overpass_query = f"""
        [out:json][timeout:15];
        (
          node["tourism"~"attraction|museum|viewpoint"](around:5000,{lat},{lon});
          way["tourism"~"attraction|museum"](around:5000,{lat},{lon});
          node["historic"~"castle|monument|memorial"](around:5000,{lat},{lon});
        );
        out center 20;
        """
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self.overpass_url, 
                    data={"data": overpass_query}, 
                    timeout=20.0
                )
                response.raise_for_status()
                data = response.json()

                places_list = []
                seen_names = set()
                
                for element in data.get("elements", []):
                    tags = element.get("tags", {})
                    
                    # Get English name preferentially
                    name = tags.get("name:en") or tags.get("name")
                    
                    if not name or name in seen_names:
                        continue
                    
                    # Skip hotels
                    tourism_type = tags.get("tourism", "")
                    if tourism_type in ["hotel", "hostel", "guest_house", "motel", "apartment"]:
                        continue
                    
                    seen_names.add(name)
                    
                    # Get coordinates
                    p_lat = element.get("lat") or element.get("center", {}).get("lat")
                    p_lon = element.get("lon") or element.get("center", {}).get("lon")
                    
                    category = self._get_category(tags)
                    
                    places_list.append(Place(
                        name=name,
                        category=category,
                        lat=p_lat,
                        lon=p_lon
                    ))

                return self._sort_by_relevance(places_list)

            except Exception as e:
                logs.log(logging.ERROR, f"Overpass API failed: {str(e)}")
                return []
    
    def _get_category(self, tags: dict) -> str:
        """Determine the category of a place from its tags."""
        if "historic" in tags:
            return "historic"
        elif tags.get("tourism") == "museum":
            return "museum"
        elif tags.get("amenity") == "place_of_worship":
            return "religious site"
        elif tags.get("tourism") == "viewpoint":
            return "viewpoint"
        elif tags.get("tourism") == "artwork":
            return "artwork"
        else:
            return tags.get("tourism", "attraction")
    
    def _sort_by_relevance(self, places: list[Place]) -> list[Place]:
        """Sort places by relevance (priority to popular categories)."""
        priority_order = {
            "historic": 1,
            "museum": 2,
            "religious site": 3,
            "attraction": 4,
            "viewpoint": 5,
            "artwork": 6
        }
        
        return sorted(places, key=lambda p: priority_order.get(p.category, 99))