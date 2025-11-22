"""
Local file-based repository for storing chat data and state.
Uses JSON files instead of MongoDB.
"""
import json
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from pathlib import Path

from app.models.base_model import ChatLog
from app.core.logger import logs
import logging


class LocalRepository:
    """Repository for storing data in local JSON files."""
    
    def __init__(self):
        """Initialize local storage directories."""
        self.base_dir = Path("data")
        self.chats_dir = self.base_dir / "chats"
        self.state_dir = self.base_dir / "state"
        self.cache_dir = self.base_dir / "cache"
        
        # Create directories if they don't exist
        self.chats_dir.mkdir(parents=True, exist_ok=True)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        logs.log(logging.INFO, "Local file repository initialized")
    
    def _get_chat_file(self, session_id: str) -> Path:
        """Get the file path for a session's chat history."""
        return self.chats_dir / f"{session_id}.json"
    
    def _get_state_file(self, session_id: str) -> Path:
        """Get the file path for a session's state."""
        return self.state_dir / f"{session_id}.json"
    
    def _get_cache_file(self, cache_key: str) -> Path:
        """Get the file path for cached data."""
        # Sanitize cache key for filename
        safe_key = cache_key.replace(":", "_").replace("/", "_")
        return self.cache_dir / f"{safe_key}.json"
    
    # ===== Chat History Methods =====
    
    async def save_chat(self, chat_log: ChatLog) -> bool:
        """Save a chat message to local file."""
        try:
            chat_file = self._get_chat_file(chat_log.session_id)
            
            # Load existing chats or create new list
            if chat_file.exists():
                with open(chat_file, 'r') as f:
                    chats = json.load(f)
            else:
                chats = []
            
            # Append new chat
            chat_data = {
                "session_id": chat_log.session_id,
                "user_message": chat_log.user_message,
                "bot_response": chat_log.bot_response,
                "timestamp": chat_log.timestamp.isoformat() if chat_log.timestamp else datetime.now().isoformat()
            }
            chats.append(chat_data)
            
            # Save to file
            with open(chat_file, 'w') as f:
                json.dump(chats, f, indent=2)
            
            return True
        except Exception as e:
            logs.log(logging.ERROR, f"Failed to save chat: {str(e)}")
            return False
    
    async def get_chat_history(self, session_id: str, limit: int = 10) -> list[dict]:
        """Retrieve chat history for a session."""
        try:
            chat_file = self._get_chat_file(session_id)
            
            if not chat_file.exists():
                return []
            
            with open(chat_file, 'r') as f:
                chats = json.load(f)
            
            # Return last N chats
            return chats[-limit:] if limit else chats
        except Exception as e:
            logs.log(logging.ERROR, f"Failed to get chat history: {str(e)}")
            return []
    
    # ===== Session State Methods =====
    
    async def get_session_state(self, session_id: str) -> Optional[dict]:
        """Retrieve session state from local file."""
        try:
            state_file = self._get_state_file(session_id)
            
            if not state_file.exists():
                return None
            
            with open(state_file, 'r') as f:
                state_data = json.load(f)
            
            return state_data
        except Exception as e:
            logs.log(logging.ERROR, f"Failed to get session state: {str(e)}")
            return None
    
    async def update_session_state(self, session_id: str, state_data: dict) -> bool:
        """Update session state in local file."""
        try:
            state_file = self._get_state_file(session_id)
            
            # Load existing state or create new
            if state_file.exists():
                with open(state_file, 'r') as f:
                    existing_state = json.load(f)
            else:
                existing_state = {
                    "session_id": session_id,
                    "current_location": None,
                    "shown_places": [],
                    "last_updated": None
                }
            
            # Update with new data
            existing_state.update(state_data)
            existing_state["last_updated"] = datetime.now().isoformat()
            
            # Save to file
            with open(state_file, 'w') as f:
                json.dump(existing_state, f, indent=2)
            
            return True
        except Exception as e:
            logs.log(logging.ERROR, f"Failed to update session state: {str(e)}")
            return False
    
    # ===== Cache Methods =====
    
    async def get_valid_cache(self, lat: float, lon: float) -> dict | None:
        """
        Get cached weather data (alias for get_cached_weather).
        Compatible with WeatherRepository interface.
        """
        return await self.get_cached_weather(lat, lon)
    
    async def save_cache(self, lat: float, lon: float, data: dict) -> bool:
        """
        Save weather cache (alias for cache_weather).
        Compatible with WeatherRepository interface.
        """
        return await self.cache_weather(lat, lon, data)
    
    async def get_cached_weather(self, lat: float, lon: float) -> Optional[dict]:
        """Get cached weather data."""
        try:
            cache_key = f"weather_{lat}_{lon}"
            cache_file = self._get_cache_file(cache_key)
            
            if not cache_file.exists():
                return None
            
            with open(cache_file, 'r') as f:
                cached = json.load(f)
            
            # Check if cache is still valid (1 hour)
            cached_time = datetime.fromisoformat(cached["cached_at"])
            if datetime.now() - cached_time > timedelta(hours=1):
                cache_file.unlink()  # Delete expired cache
                return None
            
            return cached["data"]
        except Exception as e:
            logs.log(logging.ERROR, f"Failed to get cached weather: {str(e)}")
            return None
    
    async def cache_weather(self, lat: float, lon: float, weather_data: dict) -> bool:
        """Cache weather data."""
        try:
            cache_key = f"weather_{lat}_{lon}"
            cache_file = self._get_cache_file(cache_key)
            
            cached = {
                "data": weather_data,
                "cached_at": datetime.now().isoformat()
            }
            
            with open(cache_file, 'w') as f:
                json.dump(cached, f, indent=2)
            
            return True
        except Exception as e:
            logs.log(logging.ERROR, f"Failed to cache weather: {str(e)}")
            return False
    
    async def get_cached_places(self, lat: float, lon: float) -> Optional[dict]:
        """Get cached places data."""
        try:
            cache_key = f"places_{lat:.2f}_{lon:.2f}"
            cache_file = self._get_cache_file(cache_key)
            
            if not cache_file.exists():
                return None
            
            with open(cache_file, 'r') as f:
                cached = json.load(f)
            
            # Check if cache is still valid (1 hour)
            cached_time = datetime.fromisoformat(cached["cached_at"])
            if datetime.now() - cached_time > timedelta(hours=1):
                cache_file.unlink()  # Delete expired cache
                return None
            
            # Return in PlacesRepository format: {"places": [...], "timestamp": ...}
            return {
                "places": cached["data"],
                "timestamp": cached["cached_at"]
            }
        except Exception as e:
            logs.log(logging.ERROR, f"Failed to get cached places: {str(e)}")
            return None
    
    async def cache_places(self, lat: float, lon: float, places_data: list) -> bool:
        """Cache places data."""
        try:
            cache_key = f"places_{lat:.2f}_{lon:.2f}"
            cache_file = self._get_cache_file(cache_key)
            
            cached = {
                "data": places_data,
                "cached_at": datetime.now().isoformat()
            }
            
            with open(cache_file, 'w') as f:
                json.dump(cached, f, indent=2)
            
            return True
        except Exception as e:
            logs.log(logging.ERROR, f"Failed to cache places: {str(e)}")
            return False
