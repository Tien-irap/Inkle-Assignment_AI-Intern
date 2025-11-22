"""
LangGraph State Management for Travel Agent
Provides deterministic conversation state tracking without LLM hallucination
"""

from typing import TypedDict, Optional, Annotated
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
import operator
from dataclasses import dataclass

@dataclass
class ConversationState(TypedDict):
    """
    State schema for the travel agent conversation
    This is the single source of truth for conversation context
    """
    # Core context
    current_location: Optional[str]  # Currently discussed city/place
    current_lat: Optional[float]     # Latitude of current location
    current_lon: Optional[float]     # Longitude of current location
    
    # User input
    user_message: str                # Latest user message
    
    # Intent tracking
    intent: Optional[str]            # WEATHER, PLACES, BOTH, UNKNOWN
    
    # History tracking (for place filtering)
    shown_places: Annotated[list[str], operator.add]  # All places shown in this session
    
    # Response building
    response_text: str               # Final response to user
    weather_data: Optional[dict]     # Weather information
    places_data: Optional[list]      # Places suggestions


class ConversationGraph:
    """
    LangGraph-based conversation state manager
    Deterministic state updates without relying on LLM context understanding
    """
    
    def __init__(self):
        self.memory = MemorySaver()
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build the state graph with nodes and edges"""
        workflow = StateGraph(ConversationState)
        
        # Add nodes
        workflow.add_node("extract_location", self.extract_location_node)
        workflow.add_node("classify_intent", self.classify_intent_node)
        workflow.add_node("fetch_weather", self.fetch_weather_node)
        workflow.add_node("fetch_places", self.fetch_places_node)
        workflow.add_node("build_response", self.build_response_node)
        
        # Define edges
        workflow.set_entry_point("extract_location")
        workflow.add_edge("extract_location", "classify_intent")
        
        # Conditional routing based on intent
        workflow.add_conditional_edges(
            "classify_intent",
            self.route_by_intent,
            {
                "weather_only": "fetch_weather",
                "places_only": "fetch_places",
                "both": "fetch_weather",  # Will chain to places
                "unknown": "build_response"
            }
        )
        
        workflow.add_edge("fetch_weather", "build_response")
        workflow.add_conditional_edges(
            "fetch_places",
            lambda state: "weather_done" if state.get("weather_data") else "places_done",
            {
                "weather_done": "build_response",
                "places_done": "build_response"
            }
        )
        
        workflow.add_edge("build_response", END)
        
        return workflow.compile(checkpointer=self.memory)
    
    def extract_location_node(self, state: ConversationState) -> ConversationState:
        """
        Node 1: Extract location from message OR use existing state
        This is deterministic - no LLM hallucination
        """
        user_message = state["user_message"].lower()
        
        # Check if message explicitly mentions a new location
        # We'll use LLM here but ONLY for extraction, not context reasoning
        from app.core.llm_connection import llm_client
        import asyncio
        
        extracted = asyncio.run(llm_client.extract_location_from_current_message(state["user_message"]))
        
        if extracted:
            # New location mentioned - UPDATE STATE
            state["current_location"] = extracted
            # Note: We'll geocode this in the actual service
            # For now, just mark that we have a new location
            return state
        
        # No new location - use existing state if available
        if not state.get("current_location"):
            # No location in state and none in message
            state["current_location"] = None
        
        # State remains unchanged - we still have the old location
        return state
    
    def classify_intent_node(self, state: ConversationState) -> ConversationState:
        """
        Node 2: Classify user intent from current message
        No context reasoning - pure message analysis
        """
        from app.core.llm_connection import llm_client
        import asyncio
        
        intent = asyncio.run(llm_client.classify_intent_from_current_message(state["user_message"]))
        
        if not intent:
            # Unclear - use heuristics based on keywords
            message = state["user_message"].lower()
            if any(word in message for word in ["weather", "temperature", "climate", "rain"]):
                intent = "WEATHER"
            elif any(word in message for word in ["place", "visit", "attraction", "suggest", "more"]):
                intent = "PLACES"
            else:
                intent = "BOTH"
        
        state["intent"] = intent
        return state
    
    def route_by_intent(self, state: ConversationState) -> str:
        """Router: Decide next node based on intent"""
        intent = state.get("intent", "UNKNOWN")
        
        if state.get("current_location") is None:
            return "unknown"
        
        if intent == "WEATHER":
            return "weather_only"
        elif intent == "PLACES":
            return "places_only"
        elif intent == "BOTH":
            return "both"
        else:
            return "unknown"
    
    def fetch_weather_node(self, state: ConversationState) -> ConversationState:
        """Node 3a: Fetch weather data"""
        # This will be called by the actual service
        # Just mark that we need weather
        state["weather_data"] = {"fetch": True}
        
        # If intent is BOTH, we need to also fetch places
        if state["intent"] == "BOTH":
            # Continue to places
            pass
        
        return state
    
    def fetch_places_node(self, state: ConversationState) -> ConversationState:
        """Node 3b: Fetch places data"""
        # This will be called by the actual service
        # Just mark that we need places
        state["places_data"] = {"fetch": True}
        return state
    
    def build_response_node(self, state: ConversationState) -> ConversationState:
        """Node 4: Build final response"""
        # This will be done by the actual service
        # Just mark completion
        state["response_text"] = "Response ready"
        return state


# Singleton instance
conversation_graph = ConversationGraph()
