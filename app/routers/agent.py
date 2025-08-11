from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import json, httpx

from app.core.database import get_db
from app.models import Agent
from app.routers.auth import current_active_user
from app.schemas import AgentCreate, AgentUpdate
from app.utils.httpx import get_httpx_headers, httpx_base_url

router = APIRouter()

async def get_agents():
    async with httpx.AsyncClient() as client:
        try:
            headers = get_httpx_headers()
            response = await client.get(f"{httpx_base_url}/agents", headers=headers)
            if response.status_code != 200 and response.status_code != 201:
                raise HTTPException(status_code=response.status_code, detail=response.text or "Unknown Error")
            return response.json()
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

async def get_agent_by_id(agent_id: str):
    async with httpx.AsyncClient() as client:
        try:
            headers = get_httpx_headers()
            response = await client.get(f"{httpx_base_url}/agents/{agent_id}", headers=headers)
            if response.status_code != 200 and response.status_code != 201:
                raise HTTPException(status_code=response.status_code, detail=response.text or "Unknown Error")
            return response.json()
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

@router.get("/")
async def get_agents_db(db: AsyncSession = Depends(get_db), user = Depends(current_active_user)):
    try:
        result = await db.execute(select(Agent).where(Agent.user_id == user.id))
        return result.scalars().all()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/")
async def create_agent(agent: AgentCreate, db: AsyncSession = Depends(get_db), user = Depends(current_active_user)):
    async with httpx.AsyncClient() as client:
        try:
            headers = get_httpx_headers()
            response = await client.post(f"{httpx_base_url}/agents", data=json.dumps(agent.model_dump()), headers=headers)
            if response.status_code != 200 and response.status_code != 201:
                raise HTTPException(status_code=response.status_code, detail=response.text or "Unknown Error")
            data = response.json()
            db_agent = Agent(
                id = data.get("id"),
                name = agent.name,
                config = agent.config,
                user_id = user.id,
                created_at = data.get("created_at"),
            )
            db.add(db_agent)
            try:
                await db.commit()
                await db.refresh(db_agent)
            except Exception as e:
                print(f"Error while saving agent: {str(e)}")
            return response.json()
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

@router.get("/{agent_id}")
async def get_agent_by_id_db(agent_id: str, db: AsyncSession = Depends(get_db), user = Depends(current_active_user)):
    try:
        result = await db.execute(select(Agent).where(Agent.user_id == user.id, Agent.id == agent_id))
        return result.scalar_one_or_none()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{agent_id}")
async def update_agent(agent_id: str, agent: AgentUpdate, db: AsyncSession = Depends(get_db), user = Depends(current_active_user)):
    result = await db.execute(select(Agent).where(Agent.id == agent_id, Agent.user_id == user.id))
    db_agent = result.scalar_one_or_none()
    if not db_agent:
        raise HTTPException(status_code=404, detail=f"Not found agent {agent_id}")
    async with httpx.AsyncClient() as client:
        try:
            headers = get_httpx_headers()
            response = await client.put(f"{httpx_base_url}/agents/{agent_id}", data=json.dumps(agent.model_dump()), headers=headers)
            if response.status_code != 200 and response.status_code != 201:
                raise HTTPException(statu_code=response.status_code, detail=response.text or "Unknown Error")
            db_agent.config = {**db_agent.config, **agent.config}
            try:
                await db.commit()
                await db.refresh(db_agent)
            except Exception as e:
                print(f"Failed to save agent: {str(e)}")
            return response.text
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{agent_id}")
async def delete_agent(agent_id: str, db: AsyncSession = Depends(get_db), user = Depends(current_active_user)):
    result = await db.execute(select(Agent).where(Agent.id == agent_id, Agent.user_id == user.id))
    db_agent = result.scalar_one_or_none()
    if not db_agent:
        raise HTTPException(status_code=404, detail=f"Not found agent {agent_id}")
    async with httpx.AsyncClient() as client:
        try:
            headers = get_httpx_headers()
            response = await client.delete(f"{httpx_base_url}/agents/{agent_id}", headers=headers)
            if response.status_code != 200 and response.status_code != 201:
                raise HTTPException(status_code=response.status_code, detail=response.text or "Unknown Error")
            try:
                await db.delete(db_agent)
                await db.commit()
                await db.refresh(db_agent)
            except Exception as e:
                print(f"Failed to delete agent: {str(e)}")
            return response.text
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

@router.post("/{agent_id}/duplicate")
async def duplicate_agent(agent_id: str, db: AsyncSession = Depends(get_db), user = Depends(current_active_user)):
    result = await db.execute(select(Agent).where(Agent.id == agent_id, Agent.user_id == user.id))
    db_agent = result.scalar_one_or_none()
    if not db_agent:
        raise HTTPException(status_code=404, detail=f"Not found agent {agent_id}")
    async with httpx.AsyncClient() as client:
        try:
            headers = get_httpx_headers()
            response = await client.post(f"{httpx_base_url}/agents/{agent_id}/duplicate", headers=headers)
            if response.status_code != 200 and response.status_code != 201:
                raise HTTPException(status_code=response.status_code, detail=response.text or "Unknown Error")
            data = response.json()
            new_db_agent = Agent(
                id = data.get("id"),
                name = data.get("name"),
                config = data.get("config"),
                created_at = data.get("created_at"),
                user_id = user.id,
            )
            db.add(new_db_agent)
            try:
                await db.commit()
                await db.refresh(new_db_agent)
            except Exception as e:
                print(f"Error while saving agent: {str(e)}")
            return data
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

@router.get("/{agent_id}/call-histories")
async def get_call_histories(
    agent_id: str,
    start_at: float,
    limit: int,
    db: AsyncSession = Depends(get_db),
    user = Depends(current_active_user)
):
    result = await db.execute(select(Agent).where(Agent.id == agent_id, Agent.user_id == user.id))
    db_agent = result.scalar_one_or_none()
    if not db_agent:
        raise HTTPException(status_code=404, detail=f"Not found agent {agent_id}")
    async with httpx.AsyncClient() as client:
        try:
            headers = get_httpx_headers()
            response = await client.get(f"{httpx_base_url}/agents/{agent_id}/call-histories", headers=headers, params={ "start_at": start_at, "limit": limit })
            if response.status_code != 200 and response.status_code != 201:
                raise HTTPException(status_code=response.status_code, detail=response.text or "Unknown Error")
            return response.json()
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

@router.post("/{agent_id}/embed")
async def set_embed_config(agent_id: str, embed_config: dict, db: AsyncSession = Depends(get_db), user = Depends(current_active_user)):
    result = await db.execute(select(Agent).where(Agent.id == agent_id, Agent.user_id == user.id))
    db_agent = result.scalar_one_or_none()
    if not db_agent:
        raise HTTPException(status_code=404, detail=f"Not found agent {agent_id}")
    async with httpx.AsyncClient() as client:
        try:
            headers = get_httpx_headers()
            response = await client.post(f"{httpx_base_url}/agents/{agent_id}/embed", json=embed_config, headers=headers)
            if response.status_code != 200 and response.status_code != 201:
                raise HTTPException(status_code=response.status_code, detail=response.text or "Unknown Error")
            return response.text
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
