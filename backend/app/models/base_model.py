from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime

# --- Enums ---
class IntentType(str, Enum):
    WEATHER = "WEATHER"
    PLACES = "PLACES"
    BOTH = "BOTH"
    UNKNOWN = "UNKNOWN"

# --- Domain Models ---
class Location(BaseModel):
    name: str
    lat: float
    lon: float
    display_name: Optional[str] = None

class AgentStep(BaseModel):
    """Tracks the steps taken by the agent for debugging/UI"""
    step_name: str
    status: str  # "success", "failed", "skipped"
    details: str

# --- API Request/Response Models ---
class ChatRequest(BaseModel):
    session_id: str = Field(..., description="Unique identifier for the user session")
    message: str = Field(..., description="User's input message")

class ChatResponse(BaseModel):
    session_id: str
    message: str
    extracted_location: Optional[Location] = None
    intent: IntentType
    steps: List[AgentStep] = []
    data: Dict[str, Any] = {} # Holds the raw data from tools (weather/places)

# --- Database Models ---
class ChatLog(BaseModel):
    session_id: str
    user_message: str
    bot_response: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = {}