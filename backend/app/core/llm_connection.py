import httpx
import logging
from app.core.config import settings
from app.core.logger import logs
from app.core.llm_providers import (
    BaseLLMProvider,
    MistralProvider,
    OpenAIProvider,
    AnthropicProvider,
    GroqProvider
)

class LLMService:
    def __init__(self):
        self.provider = self._initialize_provider()
        logs.log(logging.INFO, f"🤖 LLM Provider initialized: {self.provider.get_provider_name()}")
    
    def _initialize_provider(self) -> BaseLLMProvider:
        """Initialize the selected LLM provider based on settings"""
        provider = settings.LLM_PROVIDER.lower()
        
        if provider == "mistral":
            return MistralProvider(
                api_key=settings.MISTRAL_API_KEY,
                model=settings.MISTRAL_MODEL
            )
        elif provider == "openai":
            return OpenAIProvider(
                api_key=settings.OPENAI_API_KEY,
                model=settings.OPENAI_MODEL
            )
        elif provider == "anthropic":
            return AnthropicProvider(
                api_key=settings.ANTHROPIC_API_KEY,
                model=settings.ANTHROPIC_MODEL
            )
        elif provider == "groq":
            return GroqProvider(
                api_key=settings.GROQ_API_KEY,
                model=settings.GROQ_MODEL
            )
        else:
            logs.log(logging.WARNING, f"Unknown provider '{provider}', defaulting to Mistral")
            return MistralProvider(
                api_key=settings.MISTRAL_API_KEY,
                model=settings.MISTRAL_MODEL
            )

    async def extract_location_with_context(self, user_message: str, chat_history: list = None) -> str | None:
        """
        Step A: Location Extraction with Conversation Context (FALLBACK METHOD)
        Uses LLM to extract location from conversation history when current message doesn't have one.
        This should only be called when current message extraction returns None.
        """
        system_prompt = (
            "You are a location extraction assistant with context awareness. "
            "The current message does NOT explicitly mention a location. "
            "Look at the conversation history to find the MOST RECENTLY mentioned location. "
            "The user is asking about 'there', 'some more', 'what else', etc. referring to a previous location. "
            "Identify the location from the most recent conversation and return ONLY that location name. "
            "IMPORTANT: Return ONLY ONE location name - the LAST location mentioned in the conversation. "
            "Return ONLY the location name, nothing else. "
            "If no location can be found in the history, return 'NONE'."
        )

        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history for context
        if chat_history:
            for chat in chat_history[-5:]:
                messages.append({"role": "user", "content": chat.get("user_message", "")})
                messages.append({"role": "assistant", "content": chat.get("bot_response", "")})
        
        # Add current message
        messages.append({"role": "user", "content": user_message})

        try:
            content = await self.provider.generate(messages, temperature=0.1, timeout=10.0)
            
            if content.upper() == "NONE" or not content:
                return None
            
            return content

        except Exception as e:
            logs.log(logging.ERROR, f"Location extraction with context failed: {str(e)}")
            return None

    async def extract_location_from_current_message(self, user_message: str) -> str | None:
        """
        Step A: Location Extraction from CURRENT message ONLY (no context)
        Uses LLM to extract location from the current message, ignoring any history.
        Returns None if no location is explicitly mentioned in current message.
        """
        system_prompt = (
            "You are a location extraction assistant. "
            "Extract ONLY the city or location name from THIS SPECIFIC message. "
            "Do NOT consider any previous conversation or context. "
            "If this message contains a location (city, place, country), return ONLY that location name. "
            "If this message says 'there', 'suggest more', 'what else', or does NOT explicitly mention a location, return 'NONE'. "
            "Return ONLY the location name or 'NONE', nothing else."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]

        try:
            content = await self.provider.generate(messages, temperature=0.1, timeout=10.0)
            
            if content.upper() == "NONE" or not content:
                return None
            
            logs.log(logging.INFO, f"Extracted location from current message: {content}")
            return content

        except Exception as e:
            logs.log(logging.ERROR, f"Location extraction from current message failed: {str(e)}")
            return None

    async def extract_location(self, user_message: str) -> str | None:
        """
        Step A: Location Extraction (DEPRECATED - kept for backward compatibility)
        Uses LLM to extract the city/location name from natural language.
        """
        system_prompt = (
            "You are a location extraction assistant. "
            "Extract ONLY the city or location name from the user's message. "
            "Return ONLY the location name, nothing else. "
            "If no location is mentioned, return 'NONE'."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"User said: '{user_message}'"}
        ]

        try:
            content = await self.provider.generate(messages, temperature=0.1, timeout=10.0)
            
            if content.upper() == "NONE" or not content:
                return None
            
            return content

        except Exception as e:
            logs.log(logging.ERROR, f"Location extraction failed: {str(e)}")
            return None

    async def classify_intent_from_current_message(self, user_message: str) -> str | None:
        """
        Step B: Intent Classification from CURRENT message ONLY (no context)
        Classifies intent from the current message, ignoring any history.
        Returns None if intent is ambiguous (contains words like 'there', 'more', 'else').
        """
        system_prompt = (
            "You are a travel assistant router. "
            "Classify the user's intent from THIS SPECIFIC message into exactly one of these categories: "
            "WEATHER, PLACES, BOTH, UNCLEAR. "
            "- WEATHER: if explicitly asking about weather, temperature, climate, rain, forecast, etc.\n"
            "- PLACES: if explicitly asking about places to visit, attractions, things to do, trip planning, etc.\n"
            "- BOTH: if explicitly asking about both weather AND places together in this message.\n"
            "- UNCLEAR: if the message uses vague references like 'there', 'more', 'some more', 'what else', 'other places', etc. without being specific.\n"
            "Do NOT use any previous context. Only analyze THIS message.\n"
            "Return ONLY the category name: WEATHER, PLACES, BOTH, or UNCLEAR."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]

        try:
            content = await self.provider.generate(messages, temperature=0.1, timeout=10.0)
            content = content.upper()
            
            if content == "UNCLEAR":
                logs.log(logging.INFO, f"Intent unclear from current message, will use context")
                return None
            
            if content in ["WEATHER", "PLACES", "BOTH"]:
                logs.log(logging.INFO, f"Intent classified from current message: {content}")
                return content
            
            logs.log(logging.WARNING, f"LLM returned invalid intent: {content}. Will use context.")
            return None

        except Exception as e:
            logs.log(logging.ERROR, f"Intent classification from current message failed: {str(e)}")
            return None

    async def classify_intent_with_context(self, user_message: str, chat_history: list = None) -> str:
        """
        Step B: Intent Classification with Context (FALLBACK METHOD)
        Uses conversation history to determine intent when current message is ambiguous.
        This should only be called when current message classification returns None.
        """
        system_prompt = (
            "You are a travel assistant router with context awareness. "
            "The current message is ambiguous (uses words like 'there', 'more', 'else'). "
            "Look at the conversation history to determine what the user wants. "
            "Classify into exactly one of these categories: WEATHER, PLACES, BOTH. "
            "- WEATHER: if they're following up about weather (e.g., 'what is the weather there' after discussing a location)\n"
            "- PLACES: if they're asking for more places (e.g., 'suggest some more' after seeing place suggestions)\n"
            "- BOTH: if unclear from context or they want both.\n"
            "Look at the most recent conversation to understand what they were discussing.\n"
            "Return ONLY the category name: WEATHER, PLACES, or BOTH."
        )

        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history for context
        if chat_history:
            for chat in chat_history[-3:]:
                messages.append({"role": "user", "content": chat.get("user_message", "")})
                messages.append({"role": "assistant", "content": chat.get("bot_response", "")})
        
        # Add current message
        messages.append({"role": "user", "content": user_message})

        try:
            content = await self.provider.generate(messages, temperature=0.1, timeout=10.0)
            content = content.upper()
            
            if content in ["WEATHER", "PLACES", "BOTH"]:
                return content
            
            logs.log(logging.WARNING, f"LLM returned invalid intent: {content}. Defaulting to BOTH.")
            return "BOTH"

        except Exception as e:
            logs.log(logging.ERROR, f"Intent classification with context failed: {str(e)}")
            return "BOTH"

    async def enhance_places_suggestions(self, location_name: str, existing_places: list[str]) -> list[str]:
        """
        Uses LLM to suggest popular tourist attractions for a location.
        Supplements Overpass API results with LLM knowledge.
        """
        system_prompt = (
            "You are a travel expert. Given a city/location name, suggest the most popular and must-visit tourist attractions. "
            "Return ONLY a numbered list of place names, one per line. "
            "Focus on: famous landmarks, museums, historical sites, parks, monuments, and iconic attractions. "
            "Do NOT include: hotels, restaurants, shopping malls, or generic places. "
            "Return 15-20 suggestions maximum."
        )
        
        # Build context about existing places
        existing_context = ""
        if existing_places:
            existing_context = f"\n\nPlaces already found nearby: {', '.join(existing_places[:10])}"
        
        user_prompt = f"List the top tourist attractions to visit in {location_name}.{existing_context}"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        try:
            content = await self.provider.generate(messages, temperature=0.3, timeout=15.0)
            
            # Parse the numbered list
            places = []
            for line in content.split("\n"):
                line = line.strip()
                # Remove numbering (1., 2., 1), etc.)
                if line and (line[0].isdigit() or line.startswith("-")):
                    # Remove leading numbers, dots, dashes, parentheses
                    cleaned = line.lstrip("0123456789.-) ")
                    if cleaned:
                        places.append(cleaned)
            
            logs.log(logging.INFO, f"LLM suggested {len(places)} places for {location_name}")
            return places[:20]  # Limit to 20

        except Exception as e:
            logs.log(logging.ERROR, f"LLM places suggestion failed: {str(e)}")
            return []
    
    async def get_restaurants_suggestions(self, location_name: str) -> list[str]:
        """Get top restaurant recommendations from LLM."""
        system_prompt = (
            "You are a food expert. Given a city/location, suggest the top restaurants and cafes. "
            "Include a mix of local cuisine, fine dining, and popular eateries. "
            "Return ONLY a numbered list of restaurant names, one per line. "
            "Return 8-10 suggestions maximum."
        )
        
        user_prompt = f"List the best restaurants and cafes in {location_name}."

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        try:
            content = await self.provider.generate(messages, temperature=0.3, timeout=15.0)
            
            restaurants = []
            for line in content.split("\n"):
                line = line.strip()
                if line and (line[0].isdigit() or line.startswith("-")):
                    cleaned = line.lstrip("0123456789.-) ")
                    if cleaned:
                        restaurants.append(cleaned)
            
            logs.log(logging.INFO, f"LLM suggested {len(restaurants)} restaurants for {location_name}")
            return restaurants[:10]

        except Exception as e:
            logs.log(logging.ERROR, f"LLM restaurants suggestion failed: {str(e)}")
            return []
    
    async def get_hotels_suggestions(self, location_name: str) -> list[str]:
        """Get top hotel recommendations from LLM."""
        system_prompt = (
            "You are a hospitality expert. Given a city/location, suggest the top hotels and accommodations. "
            "Include a mix of luxury hotels, boutique hotels, and popular accommodations. "
            "Return ONLY a numbered list of hotel names, one per line. "
            "Return 8-10 suggestions maximum."
        )
        
        user_prompt = f"List the best hotels and accommodations in {location_name}."

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        try:
            content = await self.provider.generate(messages, temperature=0.3, timeout=15.0)
            
            hotels = []
            for line in content.split("\n"):
                line = line.strip()
                if line and (line[0].isdigit() or line.startswith("-")):
                    cleaned = line.lstrip("0123456789.-) ")
                    if cleaned:
                        hotels.append(cleaned)
            
            logs.log(logging.INFO, f"LLM suggested {len(hotels)} hotels for {location_name}")
            return hotels[:10]

        except Exception as e:
            logs.log(logging.ERROR, f"LLM hotels suggestion failed: {str(e)}")
            return []

    async def classify_intent(self, user_message: str) -> str:
        """
        Step B: Intent Classification (The Router)
        Sends prompt to LLM to decide between WEATHER, PLACES, or BOTH.
        """
        
        system_prompt = (
            "You are a travel assistant router. "
            "Classify the user's intent into exactly one of these three categories: "
            "WEATHER, PLACES, BOTH. "
            "- WEATHER: if the user is asking about weather, temperature, climate, rain, etc.\n"
            "- PLACES: if the user is asking about places to visit, attractions, things to do, trip planning, etc.\n"
            "- BOTH: if the user is asking about both weather AND places, or it's unclear.\n"
            "Return ONLY the category name. Do not add punctuation or extra text."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"User said: '{user_message}'"}
        ]

        try:
            content = await self.provider.generate(messages, temperature=0.1, timeout=10.0)
            content = content.upper()
            
            # Simple validation to ensure LLM didn't hallucinate a new category
            if content in ["WEATHER", "PLACES", "BOTH"]:
                return content
            
            logs.log(logging.WARNING, f"LLM returned invalid intent: {content}. Defaulting to BOTH.")
            return "BOTH"

        except Exception as e:
            logs.log(logging.ERROR, f"LLM API Failed: {str(e)}")
            # Fallback mechanism if LLM is down
            return "BOTH"

# Singleton instance
llm_client = LLMService()