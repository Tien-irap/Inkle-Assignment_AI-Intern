import httpx
import re
import logging
from app.models.base_model import ChatResponse, ChatRequest, Location, IntentType, AgentStep, ChatLog
from app.repos.base_repo import ChatRepository
from app.core.logger import logs
from app.core.llm_connection import llm_client
from app.services.session_state import SessionStateManager
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
        self.db = db
        self.state_manager = SessionStateManager(db) if db is not None else None
        # Initialize child services
        if db is not None:
            self.weather_service = WeatherService(WeatherRepository(db))
            self.places_service = PlacesService(PlacesRepository(db))
        else:
            # For local storage, use the repo for caching
            self.weather_service = WeatherService(repo)
            self.places_service = PlacesService(repo)
    
    async def _get_session_state(self, session_id: str) -> dict:
        """Get session state - works with both MongoDB and local storage."""
        if self.state_manager:
            state = await self.state_manager.get_state(session_id)
            return state if isinstance(state, dict) else state.__dict__
        else:
            # Use repository's session state
            state = await self.repo.get_session_state(session_id)
            return state or {
                "current_location": None,
                "current_lat": None,
                "current_lon": None,
                "shown_places": []
            }
    
    async def _update_location(self, session_id: str, location_name: str, lat: float, lon: float):
        """Update location in state - works with both MongoDB and local storage."""
        if self.state_manager:
            await self.state_manager.update_location(session_id, location_name, lat, lon)
        else:
            # Use repository's session state
            state = await self.repo.get_session_state(session_id) or {}
            state.update({
                "current_location": location_name,
                "current_lat": lat,
                "current_lon": lon
            })
            await self.repo.update_session_state(session_id, state)
    
    async def _add_shown_places(self, session_id: str, places: list[str]):
        """Add shown places to state - works with both MongoDB and local storage."""
        if self.state_manager:
            await self.state_manager.add_shown_places(session_id, places)
        else:
            # Use repository's session state
            state = await self.repo.get_session_state(session_id) or {}
            shown_places = state.get("shown_places", [])
            shown_places.extend([p for p in places if p not in shown_places])
            state["shown_places"] = shown_places
            await self.repo.update_session_state(session_id, state)

    async def process_request(self, request: ChatRequest) -> ChatResponse:
        """
        The Brain: Orchestrates logic using LangGraph-inspired state management
        State-based approach eliminates LLM hallucination in context handling
        """
        logs.log(logging.INFO, f"Processing request for session: {request.session_id}", extra={"msg": request.message})
        
        steps = []
        response_data = {}
        
        # --- Step 0: Get Session State (THE KEY DIFFERENCE) ---
        # Load persistent state from storage - this is our "memory"
        session_state = await self._get_session_state(request.session_id)
        logs.log(logging.INFO, f"Loaded session state - current_location: {session_state.get('current_location')}")
        
        # --- Step A: Entity Extraction & Geocoding (State-based) ---
        # Strategy: Extract from current message, update STATE if found, else use STATE
        
        # 1. Try extracting location from CURRENT message ONLY
        location_query = await llm_client.extract_location_from_current_message(request.message)
        
        if location_query and location_query.upper() != "NONE":
            # NEW LOCATION FOUND - This is the "Updater" logic
            logs.log(logging.INFO, f"✨ New location mentioned: {location_query}")
            location = await self._geocode(location_query)
            
            if location:
                # UPDATE STATE - This persists across all future messages
                await self._update_location(
                    request.session_id,
                    location.name,
                    location.lat,
                    location.lon
                )
                logs.log(logging.INFO, f"✅ State updated: current_location = {location.name}")
            else:
                # Geocoding failed for extracted location
                logs.log(logging.WARNING, f"Geocoding failed for extracted location: {location_query}")
                return ChatResponse(
                    session_id=request.session_id,
                    message=f"I'm sorry, I couldn't find a location matching '{location_query}'. Could you be more specific?",
                    intent=IntentType.UNKNOWN,
                    steps=[AgentStep(step_name="Geocoding", status="failed", details=f"No results for {location_query}")]
                )
        else:
            # NO NEW LOCATION - This is the "Reader" logic
            logs.log(logging.INFO, "No new location in message, checking STATE...")
            
            # Read from STATE (not from chat history!)
            if session_state.get("current_location"):
                # We have a location in state - use it!
                location = Location(
                    name=session_state["current_location"],
                    lat=session_state["current_lat"],
                    lon=session_state["current_lon"]
                )
                logs.log(logging.INFO, f"📍 Using location from STATE: {location.name}")
            else:
                # No location in state and none in message - can't proceed
                logs.log(logging.WARNING, "No location found in message or state")
                return ChatResponse(
                    session_id=request.session_id,
                    message="I need to know which location you're interested in. Could you please mention a city or place?",
                    intent=IntentType.UNKNOWN,
                    steps=[AgentStep(step_name="Location Extraction", status="failed", details="No location in message or state")]
                )
        
        steps.append(AgentStep(step_name="Geocoding", status="success", details=f"Found {location.name}"))

        # --- Step B: Intent Classification ---
        # Simple, no context needed - just analyze current message
        
        intent_str = await llm_client.classify_intent_from_current_message(request.message)
        
        if not intent_str:
            # Use simple keyword matching as fallback
            message_lower = request.message.lower()
            if any(word in message_lower for word in ["weather", "temperature", "climate"]):
                intent_str = "WEATHER"
            elif any(word in message_lower for word in ["place", "visit", "suggest", "more"]):
                intent_str = "PLACES"
            else:
                intent_str = "BOTH"
            logs.log(logging.INFO, f"Intent determined by keywords: {intent_str}")
        
        try:
            intent = IntentType(intent_str)
        except ValueError:
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
                    all_places_objects = places_response.places  # Keep full Place objects
                    all_place_names = [place.name for place in all_places_objects]
                    
                    # Get previously shown places from STATE (not chat history!)
                    shown_places = set(session_state.get("shown_places", []))
                    logs.log(logging.INFO, f"Found {len(shown_places)} previously shown places in STATE")
                    
                    # Filter out already shown places and show up to 8 new ones
                    new_place_objects = [p for p in all_places_objects if p.name not in shown_places]
                    places_to_show_objects = new_place_objects[:8] if new_place_objects else all_places_objects[:8]
                    places_to_show_names = [p.name for p in places_to_show_objects]
                    
                    # Update STATE with newly shown place names
                    await self._add_shown_places(request.session_id, places_to_show_names)
                    
                    # Store full Place objects for response formatting
                    places_data = [p.dict() for p in places_to_show_objects]
                    response_data["places"] = places_data
                    
                    if shown_places and new_place_objects:
                        steps.append(AgentStep(step_name="Places Agent", status="success", details=f"Found {len(places_to_show_objects)} new places (filtered {len(shown_places)} already shown)"))
                    else:
                        steps.append(AgentStep(step_name="Places Agent", status="success", details=f"Found {len(places_data)} places"))
                except Exception as e:
                    logs.log(logging.ERROR, f"Places service error: {str(e)}")
                    steps.append(AgentStep(step_name="Places Agent", status="failed", details=str(e)))
            else:
                steps.append(AgentStep(step_name="Places Agent", status="skipped", details="Service not initialized"))
        
        # Fetch restaurants and hotels separately
        if intent in [IntentType.PLACES, IntentType.BOTH]:
            try:
                # Get restaurants
                restaurants = await llm_client.get_restaurants_suggestions(location.name)
                response_data["restaurants"] = [{"name": r} for r in restaurants[:5]]
                steps.append(AgentStep(step_name="Restaurants Agent", status="success", details=f"Found {len(restaurants[:5])} restaurants"))
                
                # Get hotels
                hotels = await llm_client.get_hotels_suggestions(location.name)
                response_data["hotels"] = [{"name": h} for h in hotels[:5]]
                steps.append(AgentStep(step_name="Hotels Agent", status="success", details=f"Found {len(hotels[:5])} hotels"))
            except Exception as e:
                logs.log(logging.ERROR, f"Restaurants/Hotels fetch error: {str(e)}")

        # --- Finalize ---
        # Detect if this is a follow-up request (simple keyword matching)
        is_followup = any(
            keyword in request.message.lower() 
            for keyword in ["more", "else", "other", "another", "additional"]
        )
        
        final_msg = self._construct_response_text(intent, location, response_data, is_followup, request.message)
        
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

    def _generate_greeting(self, user_message: str, location_name: str, intent: IntentType) -> str:
        """Generate a natural, conversational greeting based on user's message."""
        message_lower = user_message.lower()
        
        # Detect planning/travel intent
        if any(word in message_lower for word in ["planning", "plan", "thinking", "going", "visit", "trip"]):
            greetings = [
                f"Great choice! {location_name} is a wonderful destination. ",
                f"Excellent! {location_name} is an amazing place to visit. ",
                f"How exciting! {location_name} awaits you. ",
                f"Perfect! You'll love {location_name}. "
            ]
            import random
            return random.choice(greetings)
        
        # Detect time-specific queries (this week, weekend, etc.)
        if any(word in message_lower for word in ["this week", "weekend", "next week", "soon"]):
            return f"Planning a trip to {location_name} soon? Here's what you need to know: "
        
        # Follow-up queries
        if any(word in message_lower for word in ["more", "else", "other", "additional"]):
            return "Sure, here's more information: "
        
        # Default - simple acknowledgment
        return ""
    
    def _construct_response_text(self, intent: IntentType, loc: Location, data: dict, is_followup: bool = False, user_message: str = "") -> str:
        """Constructs a natural, human-like response based on intent and data."""
        parts = []
        
        # Add conversational greeting
        if not is_followup:
            greeting = self._generate_greeting(user_message, loc.name, intent)
            if greeting:
                parts.append(greeting)
        
        # Handle different intent combinations
        if intent == IntentType.WEATHER and "weather" in data:
            weather = data["weather"]
            weather_text = self._format_weather(loc.name, weather, include_recommendation=True)
            parts.append(weather_text)
            
        elif intent == IntentType.PLACES and "places" in data:
            places_list = data.get("places", [])
            restaurants_list = data.get("restaurants", [])
            hotels_list = data.get("hotels", [])
            
            if places_list:
                # Tourist Attractions Section
                if is_followup:
                    parts.append(f"Here are some more great suggestions for {loc.name}:")
                else:
                    parts.append(f"\n🗺️ **Places to Visit in {loc.name}:**")
                
                for place_dict in places_list:
                    place_text = self._format_place(place_dict)
                    parts.append(place_text)
                
                # Restaurants Section
                if restaurants_list:
                    parts.append(f"\n\n🍽️ **Top Restaurants:**")
                    for restaurant in restaurants_list:
                        parts.append(f"  • **{restaurant['name']}**")
                
                # Hotels Section
                if hotels_list:
                    parts.append(f"\n\n🏨 **Recommended Hotels:**")
                    for hotel in hotels_list:
                        parts.append(f"  • **{hotel['name']}**")
                
                # Add helpful tip
                if not is_followup:
                    parts.append(f"\n\n💡 *Tip: Ask me for 'more places' to see additional recommendations!*")
            else:
                if is_followup:
                    parts.append(f"I've shown you all available recommendations for {loc.name}. You're all set for an amazing trip!")
                else:
                    parts.append(f"I couldn't find any recommendations for {loc.name} at the moment. Try asking about a nearby major city!")
                
        elif intent == IntentType.BOTH:
            # Handle combined weather and places
            if "weather" in data:
                weather = data["weather"]
                # Add weather with travel recommendation
                weather_text = self._format_weather(loc.name, weather, include_recommendation=True)
                parts.append(weather_text)
            
            if "places" in data:
                places_list = data.get("places", [])
                restaurants_list = data.get("restaurants", [])
                hotels_list = data.get("hotels", [])
                
                if places_list:
                    parts.append("")  # Empty line for spacing
                    
                    # Tourist Attractions
                    if is_followup:
                        parts.append(f"Here are more great recommendations:")
                    else:
                        parts.append(f"\n🗺️ **Places to Visit:**")
                    
                    for place_dict in places_list:
                        place_text = self._format_place(place_dict)
                        parts.append(place_text)
                    
                    # Restaurants Section
                    if restaurants_list:
                        parts.append(f"\n\n🍽️ **Top Restaurants:**")
                        for restaurant in restaurants_list:
                            parts.append(f"  • **{restaurant['name']}**")
                    
                    # Hotels Section
                    if hotels_list:
                        parts.append(f"\n\n🏨 **Recommended Hotels:**")
                        for hotel in hotels_list:
                            parts.append(f"  • **{hotel['name']}**")
                    
                    # Add encouraging note
                    if not is_followup:
                        parts.append(f"\n\n✨ Have a fantastic trip to {loc.name}!")
        
        return "\n".join(parts) if parts else f"I found information about {loc.name}, but couldn't retrieve specific details."
    
    def _format_weather(self, location_name: str, weather: dict, include_recommendation: bool = False) -> str:
        """Formats weather data into a readable string with travel recommendations."""
        lines = []
        
        # Current weather
        temp = weather.get("temperature")
        condition = weather.get("condition")
        feels_like = weather.get("feels_like")
        rain_prob = weather.get("rain_probability")
        humidity = weather.get("humidity")
        wind_speed = weather.get("wind_speed")
        
        lines.append(f"\n🌤️ **Weather in {location_name}:**")
        
        # Main weather line with more natural language
        weather_line = f"Right now, it's {temp}°C with {condition.lower()}"
        
        # Add feels like if different
        if feels_like and abs(feels_like - temp) > 2:
            if feels_like > temp:
                weather_line += f" (feels warmer at {feels_like}°C)"
            else:
                weather_line += f" (feels cooler at {feels_like}°C)"
        
        weather_line += "."
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
            
            # Build summary with natural language
            summary = f"📅 **This Week:** Temperatures will range from {min_temp:.0f}°C to {max_temp:.0f}°C"
            
            if rainy_days > 0:
                summary += f", with rain expected on {rainy_days} day{'s' if rainy_days > 1 else ''}."
            else:
                summary += f". Expect mostly {most_common.lower()} conditions."
            
            lines.append(summary)
            
            # Add travel recommendation based on weather
            if include_recommendation:
                lines.append("")
                recommendation = self._get_weather_recommendation(temp, rain_prob, rainy_days, condition)
                if recommendation:
                    lines.append(f"💡 **Travel Tip:** {recommendation}")
        
        return "\n".join(lines)
    
    def _get_weather_recommendation(self, temp: float, rain_prob: int, rainy_days: int, condition: str) -> str:
        """Generate travel recommendation based on weather conditions."""
        recommendations = []
        
        # Temperature-based recommendations
        if temp < 10:
            recommendations.append("Pack warm clothes and layers!")
        elif temp > 30:
            recommendations.append("It's hot! Stay hydrated and use sunscreen.")
        elif 15 <= temp <= 25:
            recommendations.append("Perfect weather for sightseeing!")
        
        # Rain-based recommendations
        if rain_prob > 60 or rainy_days >= 3:
            recommendations.append("Don't forget your umbrella and rain jacket.")
        elif rainy_days == 0 and "Clear" in condition:
            recommendations.append("Great weather for outdoor activities!")
        
        return " ".join(recommendations) if recommendations else "Have a wonderful trip!"
    
    def _format_place(self, place_dict: dict) -> str:
        """Format a place with its name."""
        name = place_dict.get("name", "Unknown")
        return f"  • **{name}**"
        