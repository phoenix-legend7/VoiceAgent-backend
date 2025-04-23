from fastapi import APIRouter
from app.core.config import settings
from app.routers import health
from app.routers import agent
from app.routers import chat
from app.routers import voice
from app.routers import call
from app.routers import sip
from app.routers import phone
from app.routers import call_logs
from app.routers import knowledge
from app.routers import campaigns

api_router = APIRouter(prefix=settings.API_V1_STR)

api_router.include_router(health.router, tags=["health"])
api_router.include_router(agent.router, prefix="/agent", tags=["agent"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(voice.router, prefix="/voice", tags=["voice"])
api_router.include_router(call.router, tags=["call"])
api_router.include_router(sip.router, tags=["sip"])
api_router.include_router(phone.router, tags=["phone"])
api_router.include_router(call_logs.router, prefix="/call-logs", tags=["call_logs"])
api_router.include_router(knowledge.router, prefix="/knowledge", tags=["knowledge"])
api_router.include_router(campaigns.router, prefix="/campaigns", tags=["campaigns"])
