from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime, timedelta

class PlacesRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db["places_cache"]

    async def get_cached_places(self, lat: float, lon: float) -> dict | None:
        """
        Checks if we have places data for these coordinates that is less than 1 hour old.
        We round to 2 decimal places (~1.1km) to group nearby queries.
        """
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        
        return await self.collection.find_one({
            "lat": round(lat, 2),
            "lon": round(lon, 2),
            "timestamp": {"$gt": one_hour_ago}
        })

    async def cache_places(self, lat: float, lon: float, places: list):
        """
        Upserts the places data.
        """
        await self.collection.update_one(
            {"lat": round(lat, 2), "lon": round(lon, 2)},
            {"$set": {"places": places, "timestamp": datetime.utcnow()}},
            upsert=True
        )