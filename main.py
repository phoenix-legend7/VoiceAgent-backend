from apscheduler.schedulers.asyncio import AsyncIOScheduler
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import nest_asyncio

from app.core.config import settings
from app.core.database import Base, engine
from app.utils.log import check_folder_exist
from app.routers.api import api_router
from app.routers.call_logs import get_all_logs, get_next_logs
from app.services.campaign_scheduler import campaign_scheduler

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

async def init_models():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Get the current event loop
    loop = asyncio.get_running_loop()
    
    # Create scheduler with the current event loop
    scheduler = AsyncIOScheduler(event_loop=loop)
    
    # Add jobs to scheduler
    scheduler.add_job(get_next_logs, trigger='interval', seconds=10, id='get_next_logs')
    
    # Start scheduler
    # scheduler.start()
    
    # Initialize database
    await init_models()
    
    # Start campaign scheduler
    await campaign_scheduler.start()
    
    # Ensure folder exists
    check_folder_exist()
    
    # Start background task in the same event loop
    # logs_task = asyncio.create_task(get_all_logs())
    
    yield
    
    # Cleanup
    scheduler.remove_job('get_next_logs')
    scheduler.shutdown()
    campaign_scheduler.shutdown()
    
    # Cancel and wait for background task
    # logs_task.cancel()
    # try:
    #     await logs_task
    # except asyncio.CancelledError:
    #     pass

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
# app.get("/all_log", tags=["Fetch log"])(get_msg_log)

@app.get("/")
async def root():
    return {"message": "Welcome to Ellisia Partner's Voice Agent API"}

import uvicorn

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
