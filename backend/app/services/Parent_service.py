import httpx
import re
import logging
from app.models.base_model import ChatResponse, ChatRequest, Location, IntentType, AgentStep, ChatLog
from app.repos.base_repo import ChatRepository
from app.core.logger import logs
from app.core.llm_connection import llm_client
from app.services.Weather_service import WeatherService
from app.services.Places_service import PlacesService
from app.repos.weather_repo import WeatherRepository
from app.repos.places_repo import PlacesRepository
from app.core.db_connection import get_db
from motor.motor_asyncio import AsyncIOMotorDatabase 

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"

class ParentAgent:
    def __init__(self, repo: ChatRepository, db: AsyncIOMotorDatabase = None):
        self.repo = repo
        # Initialize child services
        if db is not None:
            self.weather_service = WeatherService(WeatherRepository(db))
            self.places_service = PlacesService(PlacesRepository(db))
        else:
            self.weather_service = None
            self.places_service = None

    async def process_request(self, request: ChatRequest) -> ChatResponse:
        """
        The Brain: Orchestrates the logic flow A -> B -> C with conversation context
        """
        logs.log(logging.INFO, f"Processing request for session: {request.session_id}", extra={"msg": request.message})
        
        steps = []
        response_data = {}
        
        # --- Step A: Entity Extraction & Geocoding (The Guardrail) ---
        # Strategy: Try current message first, only use context as fallback
        
        # 1. First, try extracting location from CURRENT message ONLY (no context)
        location_query = await llm_client.extract_location_from_current_message(request.message)
        
        if location_query:
            logs.log(logging.INFO, f"Location found in current message: {location_query}")
            # Location found! Proceed directly to geocoding
            location = await self._geocode(location_query)
        else:
            # No location in current message, now use context as fallback
            logs.log(logging.INFO, "No location in current message, checking context...")
            
            # Get conversation history for context
            chat_history = await self.repo.get_chat_history(request.session_id, limit=10)
            logs.log(logging.INFO, f"Retrieved {len(chat_history)} previous messages for context")
            
            # Try context-aware extraction
            location_query = await llm_client.extract_location_with_context(request.message, chat_history)
            
            if not location_query:
                # Final fallback to basic cleaning
                location_query = self._clean_query_for_geocoding(request.message)
            
            logs.log(logging.INFO, f"Extracted location from context: {location_query}")
            location = await self._geocode(location_query)
        
        # Get chat history for intent classification (needed regardless)
        if 'chat_history' not in locals():
            chat_history = await self.repo.get_chat_history(request.session_id, limit=10)

        if not location:
            logs.log(logging.WARNING, f"Geocoding failed for query: {location_query}")
            return ChatResponse(
                session_id=request.session_id,
                message=f"I'm sorry, I couldn't find a location matching '{location_query}'. Could you be more specific?",
                intent=IntentType.UNKNOWN,
                steps=[AgentStep(step_name="Geocoding", status="failed", details=f"No results for {location_query}")]
            )
        
        steps.append(AgentStep(step_name="Geocoding", status="success", details=f"Found {location.name}"))

        # --- Step B: Intent Classification (The Router) ---
        # Strategy: Try current message first, only use context as fallback
        
        # 1. First, try classifying intent from CURRENT message ONLY (no context)
        intent_str = await llm_client.classify_intent_from_current_message(request.message)
        
        if not intent_str:
            # Intent unclear from current message, use context as fallback
            logs.log(logging.INFO, "Intent unclear from current message, checking context...")
            intent_str = await llm_client.classify_intent_with_context(request.message, chat_history)
        
        try:
            intent = IntentType(intent_str)
        except ValueError:
            # Fallback if LLM returns something unexpected
            intent = IntentType.BOTH 
            logs.log(logging.WARNING, f"LLM returned undefined intent '{intent_str}', defaulting to BOTH")

        steps.append(AgentStep(step_name="Intent Classification", status="success", details=f"LLM decided: {intent.value}"))

        # --- Step C: Execution (The Children) ---
        # Call actual Weather and Places services
        
        weather_data = None
        places_data = None
        
        if intent in [IntentType.WEATHER, IntentType.BOTH]:
            if self.weather_service:
                try:
                    weather_response = await self.weather_service.get_weather(location.lat, location.lon)
                    weather_data = {
                        "temperature": weather_response.temperature,
                        "condition": weather_response.condition,
                        "feels_like": weather_response.feels_like,
                        "humidity": weather_response.humidity,
                        "wind_speed": weather_response.wind_speed,
                        "rain_probability": weather_response.rain_probability,
                        "daily_forecast": [
                            {
                                "date": f.date.isoformat(),
                                "max_temp": f.max_temp,
                                "min_temp": f.min_temp,
                                "condition": f.condition,
                                "rain_probability": f.rain_probability
                            }
                            for f in weather_response.daily_forecast
                        ] if weather_response.daily_forecast else []
                    }
                    response_data["weather"] = weather_data
                    steps.append(AgentStep(step_name="Weather Agent", status="success", details=f"Fetched: {weather_response.condition}"))
                except Exception as e:
                    logs.log(logging.ERROR, f"Weather service error: {str(e)}")
                    steps.append(AgentStep(step_name="Weather Agent", status="failed", details=str(e)))
            else:
                steps.append(AgentStep(step_name="Weather Agent", status="skipped", details="Service not initialized"))

        if intent in [IntentType.PLACES, IntentType.BOTH]:
            if self.places_service:
                try:
                    places_response = await self.places_service.get_places(location.lat, location.lon, location.name)
                    all_places = [place.name for place in places_response.places]
                    
                    # Get previously shown places from chat history
                    shown_places = set()
                    for chat in chat_history:
                        # Extract places from previous responses
                        bot_msg = chat.get("bot_response", "")
                        if "places you can" in bot_msg.lower() or "these are the places" in bot_msg.lower():
                            # Extract place names from the response (lines starting with -)
                            lines = bot_msg.split("\n")
                            for line in lines:
                                line_stripped = line.strip()
                                if line_stripped.startswith("- "):
                                    place_name = line_stripped[2:].strip()  # Remove "- " prefix
                                    if place_name:
                                        shown_places.add(place_name)
                    
                    logs.log(logging.INFO, f"Found {len(shown_places)} previously shown places in chat history")
                    
                    # Filter out already shown places and show up to 8 new ones
                    new_places = [p for p in all_places if p not in shown_places]
                    places_to_show = new_places[:8] if new_places else all_places[:8]
                    
                    places_data = places_to_show
                    response_data["places"] = places_data
                    
                    if shown_places and new_places:
                        steps.append(AgentStep(step_name="Places Agent", status="success", details=f"Found {len(places_to_show)} new places (filtered {len(shown_places)} already shown)"))
                    else:
                        steps.append(AgentStep(step_name="Places Agent", status="success", details=f"Found {len(places_data)} places"))
                except Exception as e:
                    logs.log(logging.ERROR, f"Places service error: {str(e)}")
                    steps.append(AgentStep(step_name="Places Agent", status="failed", details=str(e)))
            else:
                steps.append(AgentStep(step_name="Places Agent", status="skipped", details="Service not initialized"))

        # --- Finalize ---
        # Detect if this is a follow-up request
        is_followup = len(chat_history) > 0 and any(
            keyword in request.message.lower() 
            for keyword in ["more", "else", "other", "another", "additional"]
        )
        
        final_msg = self._construct_response_text(intent, location, response_data, is_followup)
        
        # Async Save to DB
        await self.repo.save_chat(ChatLog(
            session_id=request.session_id,
            user_message=request.message,
            bot_response=final_msg
        ))

        return ChatResponse(
            session_id=request.session_id,
            message=final_msg,
            extracted_location=location,
            intent=intent,
            steps=steps,
            data=response_data
        )

    def _clean_query_for_geocoding(self, message: str) -> str:
        """
        Basic entity extraction logic.
        Removes common stop words to help Nominatim find the city.
        """
        # List of filler words to remove
        stop_words = ["weather", "places", "show", "me", "plan", "a", "trip", "to", "in", "at", "for", "the", "like", "i", "want", "go"]
        
        words = message.split()
        # Filter out stop words (case-insensitive)
        clean_words = [w for w in words if w.lower() not in stop_words]
        
        clean_query = " ".join(clean_words).strip(".,!?")
        
        # Fallback: if we stripped everything, use original message
        return clean_query if clean_query else message

    async def _geocode(self, query: str) -> Location | None:
        """
        Calls Nominatim API to get lat/lon.
        """
        async with httpx.AsyncClient() as client:
            try:
                headers = {'User-Agent': 'TravelAgentBot/1.0'}
                resp = await client.get(
                    NOMINATIM_URL, 
                    params={'q': query, 'format': 'json', 'limit': 1},
                    headers=headers,
                    timeout=5.0
                )
                resp.raise_for_status()
                data = resp.json()
                
                if data and len(data) > 0:
                    item = data[0]
                    return Location(
                        name=query,
                        lat=float(item['lat']),
                        lon=float(item['lon']),
                        display_name=item['display_name']
                    )
                return None
            except Exception as e:
                logs.log(logging.ERROR, f"Geocoding API error: {str(e)}")
                return None

    def _construct_response_text(self, intent: IntentType, loc: Location, data: dict, is_followup: bool = False) -> str:
        """Constructs a natural, human-like response based on intent and data."""
        parts = []
        
        # Handle different intent combinations
        if intent == IntentType.WEATHER and "weather" in data:
            weather = data["weather"]
            parts.append(self._format_weather(loc.name, weather))
            
        elif intent == IntentType.PLACES and "places" in data:
            places_list = data.get("places", [])
            if places_list:
                # Use different phrasing for follow-up requests
                if is_followup:
                    parts.append(f"Here are some more places you can visit in {loc.name}:")
                else:
                    parts.append(f"In {loc.name} these are the places you can go:")
                for place in places_list:
                    parts.append(f"- {place}")
            else:
                if is_followup:
                    parts.append(f"I've shown you all the available tourist attractions in {loc.name}.")
                else:
                    parts.append(f"I couldn't find any tourist attractions in {loc.name} at the moment.")
                
        elif intent == IntentType.BOTH:
            # Handle combined weather and places
            if "weather" in data:
                weather = data["weather"]
                parts.append(self._format_weather(loc.name, weather))
            
            if "places" in data:
                places_list = data.get("places", [])
                if places_list:
                    parts.append("")  # Empty line for spacing
                    if is_followup:
                        parts.append(f"Here are some more places you can visit in {loc.name}:")
                    else:
                        parts.append(f"And these are the places you can go:")
                    for place in places_list:
                        parts.append(f"- {place}")
        
        return "\n".join(parts) if parts else f"I found information about {loc.name}, but couldn't retrieve specific details."
    
    def _format_weather(self, location_name: str, weather: dict) -> str:
        """Formats weather data into a readable string."""
        lines = []
        
        # Current weather
        temp = weather.get("temperature")
        condition = weather.get("condition")
        feels_like = weather.get("feels_like")
        rain_prob = weather.get("rain_probability")
        humidity = weather.get("humidity")
        wind_speed = weather.get("wind_speed")
        
        # Main weather line
        weather_line = f"In {location_name} it's currently {temp}°C with {condition}."
        
        # Add feels like if different
        if feels_like and abs(feels_like - temp) > 2:
            weather_line += f" Feels like {feels_like}°C."
        
        lines.append(weather_line)
        
        # Additional details
        details = []
        if rain_prob is not None and rain_prob > 0:
            details.append(f"{rain_prob}% chance of rain")
        if humidity is not None:
            details.append(f"humidity {humidity}%")
        if wind_speed is not None:
            details.append(f"wind {wind_speed} km/h")
        
        if details:
            lines.append(f"({', '.join(details)})")
        
        # Weekly forecast summary
        daily_forecast = weather.get("daily_forecast", [])
        if daily_forecast:
            lines.append("")
            
            # Calculate weekly summary
            temps = [day["max_temp"] for day in daily_forecast]
            max_temp = max(temps)
            min_temp = min([day["min_temp"] for day in daily_forecast])
            
            # Count rainy days
            rainy_days = sum(1 for day in daily_forecast if day["rain_probability"] > 40)
            
            # Most common condition
            conditions = [day["condition"] for day in daily_forecast]
            most_common = max(set(conditions), key=conditions.count)
            
            # Build summary
            summary = f"📅 Week ahead: Expect temperatures between {min_temp:.0f}°C and {max_temp:.0f}°C"
            
            if rainy_days > 0:
                summary += f", with rain likely on {rainy_days} day{'s' if rainy_days > 1 else ''}."
            else:
                summary += f", mostly {most_common.lower()}."
            
            lines.append(summary)
        return "\n".join(lines)
        