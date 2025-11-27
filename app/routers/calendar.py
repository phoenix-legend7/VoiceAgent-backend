from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone
from uuid import UUID
import json
import httpx

from app.core.database import get_db
from app.models import Calendar, Agent
from app.routers.auth import current_active_user
from app.schemas.calendar import CalendarCreate, CalendarUpdate, CalendarResponse
from app.utils.encryption import encrypt_value, decrypt_value
from app.utils.httpx import get_httpx_headers, httpx_base_url

router = APIRouter()

async def find_agents_using_calendar(calendar_id: UUID, calendar_name: str, db: AsyncSession, user) -> list[Agent]:
    """Find all agents that use this calendar."""
    result = await db.execute(select(Agent).where(Agent.user_id == user.id))
    agents = result.scalars().all()
    
    using_agents = []
    calendar_id_str = str(calendar_id)
    for agent in agents:
        if agent.config and isinstance(agent.config, dict):
            calendar_ids = agent.config.get("calendar_ids", [])
            # Handle both UUID strings and UUID objects in calendar_ids
            if calendar_id_str in calendar_ids or calendar_id in calendar_ids:
                using_agents.append(agent)
    
    return using_agents

async def update_agent_app_functions_on_millisai(agent: Agent, calendar: Calendar, db: AsyncSession):
    """Update agent's app_functions on MillisAI with calendar configuration."""
    if not agent.config:
        agent.config = {}
    
    app_functions = agent.config.get("app_functions", [])
    app_functions = [f for f in app_functions if f.get("name") != calendar.name]
    
    function_config = {
        "name": calendar.name,
        "credentials": {
            "api_key": decrypt_value(calendar.api_key),
            "event_type_id": calendar.event_type_id,
        }
    }
    
    if calendar.contact_method:
        function_config["credentials"]["contact_method"] = calendar.contact_method
    
    app_functions.append(function_config)
    agent.config["app_functions"] = app_functions
    
    async with httpx.AsyncClient() as client:
        try:
            headers = get_httpx_headers()
            payload = {
                "name": agent.name,
                "config": {
                    "app_functions": app_functions
                }
            }
            response = await client.put(
                f"{httpx_base_url}/agents/{agent.id}",
                data=json.dumps(payload),
                headers=headers
            )
            if response.status_code not in [200, 201]:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Failed to update agent on MillisAI: {response.text}"
                )
            
            await db.commit()
            await db.refresh(agent)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error syncing with MillisAI: {str(e)}")

async def remove_calendar_from_agent_app_functions(agent: Agent, calendar_name: str, db: AsyncSession):
    """Remove calendar function from agent's app_functions on MillisAI."""
    if not agent.config:
        return
    
    app_functions = agent.config.get("app_functions", [])
    app_functions = [f for f in app_functions if f.get("name") != calendar_name]
    agent.config["app_functions"] = app_functions
    
    async with httpx.AsyncClient() as client:
        try:
            headers = get_httpx_headers()
            payload = {
                "name": agent.name,
                "config": {
                    "app_functions": app_functions
                }
            }
            response = await client.put(
                f"{httpx_base_url}/agents/{agent.id}",
                data=json.dumps(payload),
                headers=headers
            )
            if response.status_code not in [200, 201]:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Failed to update agent on MillisAI: {response.text}"
                )
            
            await db.commit()
            await db.refresh(agent)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error syncing with MillisAI: {str(e)}")

@router.get("/", response_model=list[CalendarResponse])
async def get_calendars(
    db: AsyncSession = Depends(get_db),
    user = Depends(current_active_user)
):
    """Fetch all calendars for the current user."""
    try:
        result = await db.execute(select(Calendar).where(Calendar.user_id == user.id))
        calendars = result.scalars().all()
        return calendars
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/", response_model=CalendarResponse)
async def create_calendar(
    calendar: CalendarCreate,
    db: AsyncSession = Depends(get_db),
    user = Depends(current_active_user)
):
    """Create a new calendar."""
    try:
        encrypted_api_key = encrypt_value(calendar.api_key)
        
        db_calendar = Calendar(
            user_id=user.id,
            name=calendar.name,
            title=calendar.title,
            provider=calendar.provider,
            api_key=encrypted_api_key,
            event_type_id=calendar.event_type_id,
            contact_method=calendar.contact_method,
            created_at=int(datetime.now(timezone.utc).timestamp()),
            updated_at=int(datetime.now(timezone.utc).timestamp())
        )
        
        db.add(db_calendar)
        await db.commit()
        await db.refresh(db_calendar)
        
        return db_calendar
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{calendar_id}", response_model=CalendarResponse)
async def update_calendar(
    calendar_id: UUID,
    calendar: CalendarUpdate,
    db: AsyncSession = Depends(get_db),
    user = Depends(current_active_user)
):
    """Update an existing calendar."""
    try:
        result = await db.execute(
            select(Calendar).where(Calendar.id == calendar_id, Calendar.user_id == user.id)
        )
        db_calendar = result.scalar_one_or_none()
        
        if not db_calendar:
            raise HTTPException(status_code=404, detail=f"Calendar {calendar_id} not found")
        
        db_calendar.name = calendar.name
        db_calendar.title = calendar.title
        db_calendar.provider = calendar.provider
        db_calendar.api_key = encrypt_value(calendar.api_key)
        db_calendar.event_type_id = calendar.event_type_id
        db_calendar.contact_method = calendar.contact_method
        db_calendar.updated_at = int(datetime.now(timezone.utc).timestamp())
        
        try:
            await db.commit()
            await db.refresh(db_calendar)
        except Exception as e:
            pass
        
        using_agents = await find_agents_using_calendar(calendar_id, calendar.name, db, user)
        for agent in using_agents:
            await update_agent_app_functions_on_millisai(agent, db_calendar, db)
        
        return db_calendar
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{calendar_id}")
async def delete_calendar(
    calendar_id: UUID,
    db: AsyncSession = Depends(get_db),
    user = Depends(current_active_user)
):
    """Delete a calendar."""
    try:
        result = await db.execute(
            select(Calendar).where(Calendar.id == calendar_id, Calendar.user_id == user.id)
        )
        db_calendar = result.scalar_one_or_none()
        
        if not db_calendar:
            raise HTTPException(status_code=404, detail=f"Calendar {calendar_id} not found")
        
        calendar_name = db_calendar.name
        
        using_agents = await find_agents_using_calendar(calendar_id, calendar_name, db, user)
        calendar_id_str = str(calendar_id)
        for agent in using_agents:
            if agent.config and isinstance(agent.config, dict):
                calendar_ids = agent.config.get("calendar_ids", [])
                if calendar_id_str in calendar_ids:
                    calendar_ids.remove(calendar_id_str)
                elif calendar_id in calendar_ids:
                    calendar_ids.remove(calendar_id)
                agent.config["calendar_ids"] = calendar_ids
            
            await remove_calendar_from_agent_app_functions(agent, calendar_name, db)
        
        try:
            await db.delete(db_calendar)
            await db.commit()
        except Exception as e:
            pass
        
        return {"message": "Calendar deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

