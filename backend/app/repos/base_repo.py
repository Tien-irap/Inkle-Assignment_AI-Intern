from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime
# Make sure this import matches where your ChatLog model is
from app.models.base_model import ChatLog 

class ChatRepository:
    # The fix: Add 'db' as a parameter here
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.chats_collection = self.db["chats"]
        self.cache_collection = self.db["cache"]

    async def save_chat(self, chat_log: ChatLog):
        """Saves the conversation history asynchronously."""
        # Using model_dump() for Pydantic v2, or .dict() if you are on v1
        await self.chats_collection.insert_one(chat_log.model_dump())

    async def get_chat_history(self, session_id: str, limit: int = 10) -> list:
        """Retrieves recent chat history for a session."""
        cursor = self.chats_collection.find(
            {"session_id": session_id}
        ).sort("timestamp", -1).limit(limit)
        
        history = await cursor.to_list(length=limit)
        # Reverse to get chronological order (oldest first)
        return list(reversed(history))

    async def get_cached_weather(self, lat: float, lon: float) -> dict | None:
        """
        Checks cache for weather data for specific coords.
        """
        return await self.cache_collection.find_one({
            "type": "weather",
            "lat": round(lat, 2), 
            "lon": round(lon, 2)
        })

    async def cache_weather(self, lat: float, lon: float, data: dict):
        """Caches weather data."""
        await self.cache_collection.update_one(
            {"type": "weather", "lat": round(lat, 2), "lon": round(lon, 2)},
            {"$set": {"data": data, "timestamp": datetime.utcnow()}},
            upsert=True
        )