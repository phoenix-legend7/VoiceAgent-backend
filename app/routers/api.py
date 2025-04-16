from fastapi import APIRouter
from app.core.config import settings
from app.routers import health

api_router = APIRouter(prefix=settings.API_V1_STR)

api_router.include_router(health.router, tags=["health"])
