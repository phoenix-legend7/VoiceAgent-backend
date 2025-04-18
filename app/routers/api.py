from fastapi import APIRouter
from app.core.config import settings
from app.routers import health
from app.routers import agent
from app.routers import chat
from app.routers import voice

api_router = APIRouter(prefix=settings.API_V1_STR)

api_router.include_router(health.router, tags=["health"])
api_router.include_router(agent.router, prefix="/agent", tags=["agent"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(voice.router, prefix="/voice", tags=["voice"])

