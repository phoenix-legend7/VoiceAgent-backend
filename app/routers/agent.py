from fastapi import APIRouter, HTTPException
import json, httpx

from app.schemas import AgentCreate, AgentUpdate
from app.utils.httpx import get_httpx_headers, httpx_base_url

router = APIRouter()

@router.get("/")
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

@router.post("/")
async def create_agent(agent: AgentCreate):
    async with httpx.AsyncClient() as client:
        try:
            headers = get_httpx_headers()
            response = await client.post(f"{httpx_base_url}/agents", data=json.dumps(agent.model_dump()), headers=headers)
            if response.status_code != 200 and response.status_code != 201:
                raise HTTPException(status_code=response.status_code, detail=response.text or "Unknown Error")
            return response.json()
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

@router.get("/{agent_id}")
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

@router.put("/{agent_id}")
async def update_agent(agent_id: str, agent: AgentUpdate):
    async with httpx.AsyncClient() as client:
        try:
            headers = get_httpx_headers()
            response = await client.put(f"{httpx_base_url}/agents/{agent_id}", data=json.dumps(agent.model_dump()), headers=headers)
            if response.status_code != 200 and response.status_code != 201:
                raise HTTPException(status_code=response.status_code, detail=response.text or "Unknown Error")
            return response.text
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{agent_id}")
async def delete_agent(agent_id: str):
    async with httpx.AsyncClient() as client:
        try:
            headers = get_httpx_headers()
            response = await client.delete(f"{httpx_base_url}/agents/{agent_id}", headers=headers)
            if response.status_code != 200 and response.status_code != 201:
                raise HTTPException(status_code=response.status_code, detail=response.text or "Unknown Error")
            return response.text
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

@router.post("/{agent_id}/duplicate")
async def duplicate_agent(agent_id: str):
    async with httpx.AsyncClient() as client:
        try:
            headers = get_httpx_headers()
            response = await client.post(f"{httpx_base_url}/agents/{agent_id}/duplicate", headers=headers)
            if response.status_code != 200 and response.status_code != 201:
                raise HTTPException(status_code=response.status_code, detail=response.text or "Unknown Error")
            return response.json()
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

@router.get("/{agent_id}/call-histories")
async def get_call_histories(agent_id: str, start_at: float, limit: int):
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
async def set_embed_config(agent_id: str, embed_config: dict):
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
