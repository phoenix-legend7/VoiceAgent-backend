from fastapi import APIRouter
from app.core.config import settings
from app.routers import (
    health,
    agent,
    chat,
    dashboard,
    voice,
    call,
    sip,
    phone,
    call_logs,
    knowledge,
    campaigns,
    campaign_schedule,
    user,
)

api_router = APIRouter(prefix=settings.API_V1_STR)

api_router.include_router(health.router, tags=["health"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(agent.router, prefix="/agent", tags=["agent"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(voice.router, prefix="/voice", tags=["voice"])
api_router.include_router(call.router, tags=["call"])
api_router.include_router(sip.router, tags=["sip"])
api_router.include_router(phone.router, tags=["phone"])
api_router.include_router(call_logs.router, prefix="/call-logs", tags=["call_logs"])
api_router.include_router(knowledge.router, prefix="/knowledge", tags=["knowledge"])
api_router.include_router(campaigns.router, prefix="/campaigns", tags=["campaigns"])
api_router.include_router(campaign_schedule.router, prefix="/campaign-schedule", tags=["campaign_schedule"])
api_router.include_router(user.router, prefix="/user", tags=["user"])
