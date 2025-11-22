from fastapi import FastAPI, HTTPException, Depends
from app.models.base_model import ChatRequest, ChatResponse
from app.services.Parent_service import ParentAgent
from app.repos.base_repo import ChatRepository
from app.routes.base_chat import router
from app.routes.weather_route import router as weather_router
from app.routes.places_route import router as places_router

app = FastAPI(title="Travel Agent Brain")
app.include_router(router)
app.include_router(weather_router)
app.include_router(places_router)

# --- Health Check ---
@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "Travel Agent Brain"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)