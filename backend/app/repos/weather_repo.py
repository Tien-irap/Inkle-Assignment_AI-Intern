from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime, timedelta

class WeatherRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db["weather_cache"]

    async def get_valid_cache(self, lat: float, lon: float) -> dict | None:
        """
        Finds weather data for these coordinates that is less than 1 hour old.
        """
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        
        # We round coordinates to 2 decimal places to group nearby requests
        return await self.collection.find_one({
            "lat": round(lat, 2),
            "lon": round(lon, 2),
            "timestamp": {"$gt": one_hour_ago}
        })

    async def save_cache(self, lat: float, lon: float, data: dict):
        """
        Upserts (Update or Insert) the weather data.
        """
        await self.collection.update_one(
            {
                "lat": round(lat, 2), 
                "lon": round(lon, 2)
            },
            {
                "$set": {
                    "data": data,
                    "timestamp": datetime.utcnow()
                }
            },
            upsert=True
        )