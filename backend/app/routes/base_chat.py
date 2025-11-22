from fastapi import APIRouter, HTTPException, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Optional

from app.models.base_model import ChatRequest, ChatResponse
from app.services.Parent_service import ParentAgent
from app.repos.base_repo import ChatRepository
from app.repos.local_repo import LocalRepository
from app.core.db_connection import get_db
from app.core.config import settings
from app.core.logger import logs

router = APIRouter()

# --- Dependency Injection Helper ---
async def get_repository():
    """Get the appropriate repository based on storage mode."""
    if settings.STORAGE_MODE == "local":
        return LocalRepository()
    else:
        db = await get_db()
        return ChatRepository(db)

async def get_agent() -> ParentAgent:
    """Get Parent Agent with the appropriate repository."""
    repo = await get_repository()
    
    if settings.STORAGE_MODE == "local":
        # For local storage, pass None as db since it won't be used
        return ParentAgent(repo, None)
    else:
        db = await get_db()
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