from fastapi import APIRouter
import json

from app.utils.httpx import httpx_client
from app.schemas import AgentCreate, AgentUpdate

router = APIRouter()

@router.get("/")
async def get_agent():
    agents = await httpx_client.get("/agents")
    return agents

@router.post("/")
async def create_agent(agent: AgentCreate):
    response = await httpx_client.post("/agents", data=json.dumps(agent.model_dump()))
    return response

@router.get("/{agent_id}")
async def get_agent_by_id(agent_id: str):
    response = await httpx_client.get(f"/agents/{agent_id}")
    return response

@router.put("/{agent_id}")
async def update_agent(agent_id: str, agent: AgentUpdate):
    response = await httpx_client.put(f"/agents/{agent_id}", data=json.dumps(agent.model_dump()))
    return response

@router.delete("/{agent_id}")
async def delete_agent(agent_id: str):
    response = await httpx_client.delete(f"/agents/{agent_id}")
    return response

@router.post("/{agent_id}/duplicate")
async def duplicate_agent(agent_id: str):
    response = await httpx_client.post(f"/agents/{agent_id}/duplicate")
    return response

@router.get("/{agent_id}/call-histories")
async def get_call_histories(agent_id: str):
    response = await httpx_client.get(f"/agents/{agent_id}/call-histories")
    return response

@router.post("/{agent_id}/embed")
async def set_embed_config(agent_id: str, embed_config: dict):
    response = await httpx_client.post(f"/agents/{agent_id}/embed", json=embed_config)
    return response
