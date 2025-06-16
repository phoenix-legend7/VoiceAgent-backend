from apscheduler.schedulers.asyncio import AsyncIOScheduler
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import asyncio

from app.core.config import settings
from app.core.database import Base, engine
from app.utils.log import check_folder_exist
from app.routers.api import api_router
from app.routers.call_logs import get_all_logs, get_next_logs

async def init_models():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Get the current event loop
    loop = asyncio.get_running_loop()
    
    # Create scheduler with the current event loop
    scheduler = AsyncIOScheduler(event_loop=loop)
    scheduler.add_job(get_next_logs, trigger='interval', seconds=10)
    scheduler.start()
    
    check_folder_exist()
    asyncio.create_task(init_models())
    asyncio.create_task(get_all_logs())
    yield
    # Cleanup
    scheduler.shutdown()

app = FastAPI(
    title=settings.APP_NAME,
    description="Backend API for Ellisia Partner's Voice Agent application",
    version="0.1.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

@app.get("/")
async def root():
    return {"message": "Welcome to Ellisia Partner's Voice Agent API"}

import uvicorn

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
