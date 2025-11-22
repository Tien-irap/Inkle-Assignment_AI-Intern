"""
Session State Manager using LangGraph
Stores conversation state per session in MongoDB
"""

from typing import Dict, Optional
from datetime import datetime
from app.services.state_graph import ConversationState
from motor.motor_asyncio import AsyncIOMotorDatabase


class SessionStateManager:
    """
    Manages persistent conversation state per session using MongoDB
    This replaces chat history lookups with deterministic state tracking
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.states_collection = self.db["conversation_states"]
    
    async def get_state(self, session_id: str) -> ConversationState:
        """
        Get current conversation state for a session
        Returns default state if session is new
        """
        state_doc = await self.states_collection.find_one({"session_id": session_id})
        
        if state_doc:
            # Return existing state
            return ConversationState(
                current_location=state_doc.get("current_location"),
                current_lat=state_doc.get("current_lat"),
                current_lon=state_doc.get("current_lon"),
                user_message="",  # Will be set by current request
                intent=None,
                shown_places=state_doc.get("shown_places", []),
                response_text="",
                weather_data=None,
                places_data=None
            )
        
        # New session - return fresh state
        return ConversationState(
            current_location=None,
            current_lat=None,
            current_lon=None,
            user_message="",
            intent=None,
            shown_places=[],
            response_text="",
            weather_data=None,
            places_data=None
        )
    
    async def update_state(self, session_id: str, state: ConversationState):
        """
        Update conversation state for a session
        Only persists the context fields, not transient data
        """
        await self.states_collection.update_one(
            {"session_id": session_id},
            {
                "$set": {
                    "current_location": state.get("current_location"),
                    "current_lat": state.get("current_lat"),
                    "current_lon": state.get("current_lon"),
                    "shown_places": state.get("shown_places", []),
                    "updated_at": datetime.utcnow()
                }
            },
            upsert=True
        )
    
    async def add_shown_places(self, session_id: str, places: list[str]):
        """
        Add places to the shown_places list for this session
        Used for filtering out duplicates in follow-up requests
        """
        await self.states_collection.update_one(
            {"session_id": session_id},
            {
                "$addToSet": {"shown_places": {"$each": places}},
                "$set": {"updated_at": datetime.utcnow()}
            },
            upsert=True
        )
    
    async def clear_state(self, session_id: str):
        """Clear conversation state for a session (for testing/reset)"""
        await self.states_collection.delete_one({"session_id": session_id})
    
    async def update_location(self, session_id: str, location: str, lat: float, lon: float):
        """
        Update just the location in state
        This is the key method - deterministic location tracking
        """
        await self.states_collection.update_one(
            {"session_id": session_id},
            {
                "$set": {
                    "current_location": location,
                    "current_lat": lat,
                    "current_lon": lon,
                    "updated_at": datetime.utcnow()
                }
            },
            upsert=True
        )
