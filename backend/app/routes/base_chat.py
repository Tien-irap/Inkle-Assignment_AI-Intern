from fastapi import APIRouter, HTTPException, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

# Importing from your specific folder structure (based on screenshot)
# Ensure the classes inside these files match the names used here
try:
    # Try the structure from your screenshot
    from app.models.base_model import ChatRequest, ChatResponse
    from app.services.Parent_service import ParentAgent
    from app.repos.base_repo import ChatRepository
except ImportError:
    # Fallback to flat structure if you haven't moved the code inside the files yet
    from app.models import ChatRequest, ChatResponse
    from app.services.Parent_service import ParentAgent
    from app.repos.base_repo import ChatRepository

from app.core.db_connection import get_db
from app.core.logger import logs

router = APIRouter()

# --- Dependency Injection Helper ---
def get_repository(db: AsyncIOMotorDatabase = Depends(get_db)) -> ChatRepository:
    return ChatRepository(db)

def get_agent(repo: ChatRepository = Depends(get_repository), db: AsyncIOMotorDatabase = Depends(get_db)) -> ParentAgent:
    return ParentAgent(repo, db)

# --- The Endpoint ---
@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest, 
    agent: ParentAgent = Depends(get_agent)
):
    """
    Receives the message from Streamlit, sends it to the Parent Agent,
    and returns the structured response.
    """
    try:
        response = await agent.process_request(request)
        return response
    except Exception as e:
        logs.log(40, f"Error in chat_endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))