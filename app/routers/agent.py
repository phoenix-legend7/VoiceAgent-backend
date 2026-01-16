from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
import json, httpx, re

from app.core.database import get_db
from app.models import Agent, Tools, Calendar
from app.routers.auth import current_active_user
from app.schemas import AgentCreate, AgentUpdate
from app.utils.httpx import get_httpx_headers, httpx_base_url
from app.utils.encryption import decrypt_value
from app.services.prompt_generator import generate_prompt_with_openai


class AgentToolRequest(BaseModel):
    id: str
    timeout: int | None = None
    run_after_call: bool | None = None
    messages: list[str] | None = None
    response_mode: str | None = None
    execute_after_message: bool | None = None
    exclude_session_id: bool | None = None


class PromptGenerationRequest(BaseModel):
    agent_name: str
    industry: str
    description: str | None = None
    purpose: str | None = None
    personality: str | None = None
    industry_prompt: str | None = None


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

def to_function_name(text: str) -> str:
    # Lowercase the text
    text = text.lower()
    # Replace spaces and invalid characters with underscores
    text = re.sub(r'[^a-z0-9_]', '_', text)
    # Ensure it doesn't start with a number
    if re.match(r'^[0-9]', text):
        text = "_" + text
    # Collapse multiple underscores
    text = re.sub(r'_+', '_', text).strip('_')
    return text

@router.get("/")
async def get_agents_db(db: AsyncSession = Depends(get_db), user = Depends(current_active_user)):
    try:
        result = await db.execute(select(Agent).where(Agent.user_id == user.id))
        return result.scalars().all()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/")
async def create_agent(agent: AgentCreate, db: AsyncSession = Depends(get_db), user = Depends(current_active_user)):
    # Check if user has active subscription
    if not user.subscription_status or user.subscription_status not in ["active", "trialing"]:
        raise HTTPException(
            status_code=403,
            detail="Active subscription required to create agents. Please subscribe at A$299 per agent per month."
        )
    
    # Count current agents
    result = await db.execute(select(Agent).where(Agent.user_id == user.id))
    current_agent_count = len(result.scalars().all())
    
    # Check if user has enough subscription quantity for another agent
    subscription_quantity = user.subscription_quantity or 0
    if current_agent_count >= subscription_quantity:
        raise HTTPException(
            status_code=403,
            detail=f"You have {current_agent_count} agent(s) but only {subscription_quantity} subscription slot(s). Please upgrade your subscription to add more agents at A$299 per agent per month."
        )
    
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
            return data
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
            agent_data = agent.model_dump()

            if "config" in agent_data and isinstance(agent_data["config"], dict):
                config = agent_data["config"]
                calendar_ids = config.get("calendar_ids", [])
                
                if calendar_ids:
                    calendar_ids_list = calendar_ids if isinstance(calendar_ids, list) else [calendar_ids]
                    calendar_uuid_list = []
                    for cal_id in calendar_ids_list:
                        try:
                            if isinstance(cal_id, str):
                                calendar_uuid_list.append(UUID(cal_id))
                            else:
                                calendar_uuid_list.append(cal_id)
                        except:
                            continue
                    
                    if calendar_uuid_list:
                        calendars_result = await db.execute(
                            select(Calendar).where(
                                Calendar.id.in_(calendar_uuid_list),
                                Calendar.user_id == user.id
                            )
                        )
                        calendars = calendars_result.scalars().all()
                        app_functions = config.get("app_functions", [])
                        calendar_names = [cal.name for cal in calendars]
                        app_functions = [f for f in app_functions if f.get("name") not in calendar_names]
                        
                        for calendar in calendars:
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
                        
                        config["app_functions"] = app_functions
                else:
                    config["app_functions"] = []
                
                config_for_millisai = {k: v for k, v in config.items() if k != "calendar_ids"}
                agent_data["config"] = config_for_millisai

            response = await client.put(f"{httpx_base_url}/agents/{agent_id}", data=json.dumps(agent_data), headers=headers)
            if response.status_code != 200 and response.status_code != 201:
                raise HTTPException(status_code=response.status_code, detail=response.text or "Unknown Error")
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


@router.put("/{agent_id}/tools")
async def update_agent_tool(
    agent_id: str,
    tools: list[AgentToolRequest],
    db: AsyncSession = Depends(get_db),
    user = Depends(current_active_user)
):
    result = await db.execute(select(Agent).where(Agent.id == agent_id, Agent.user_id == user.id))
    db_agent = result.scalar_one_or_none()
    if not db_agent:
        raise HTTPException(status_code=404, detail=f"Not found agent {agent_id}")
    agent_tools = []
    for tool in tools:
        result = await db.execute(select(Tools).where(Tools.id == tool.id, Tools.user_id == user.id))
        db_tool = result.scalar_one_or_none()
        if not db_tool:
            raise HTTPException(status_code=404, detail=f"Not found tool {tool.id}")
        agent_tool = {
            "name": to_function_name(db_tool.name) if db_tool.tool_id == "custom" else to_function_name(db_tool.tool_id),
            "description": db_tool.description,
            "webhook": db_tool.webhook,
            "method": db_tool.method,
        }
        if db_tool.params is not None:
            agent_tool["params"] = db_tool.params
        if db_tool.header is not None:
            agent_tool["header"] = db_tool.header
        if tool.timeout is not None:
            agent_tool["timeout"] = tool.timeout
        if tool.run_after_call is not None:
            agent_tool["run_after_call"] = tool.run_after_call
        if tool.messages is not None:
            agent_tool["messages"] = tool.messages
        if tool.response_mode is not None:
            agent_tool["response_mode"] = tool.response_mode
        if tool.execute_after_message is not None:
            agent_tool["execute_after_message"] = tool.execute_after_message
        if tool.exclude_session_id is not None:
            agent_tool["exclude_session_id"] = tool.exclude_session_id
        agent_tools.append(agent_tool)

    async with httpx.AsyncClient() as client:
        try:
            headers = get_httpx_headers()
            payload = {
                "name": db_agent.name,
                "config": {
                    "tools": agent_tools,
                }
            }
            response = await client.put(f"{httpx_base_url}/agents/{agent_id}", data=json.dumps(payload), headers=headers)
            if response.status_code != 200 and response.status_code != 201:
                raise HTTPException(status_code=response.status_code, detail=response.text or "Unknown Error")
            db_agent.config = {**db_agent.config, "tools": agent_tools}
            # Convert tools to dict format for database storage
            tools_data = [tool.model_dump() for tool in tools]
            db_agent.tools = tools_data
            try:
                await db.commit()
                await db.refresh(db_agent)
            except Exception as e:
                print(f"Failed to update tools: {str(e)}")
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

@router.post("/generate-prompt")
async def generate_agent_prompt(
    request: PromptGenerationRequest,
    user = Depends(current_active_user)
):
    """
    Generate an AI agent prompt using OpenAI based on agent specifications.
    
    Args:
        request: PromptGenerationRequest containing agent details

    Returns:
        Generated prompt string
    """
    try:
        prompt = await generate_prompt_with_openai(
            agent_name=request.agent_name,
            industry=request.industry,
            description=request.description,
            purpose=request.purpose,
            personality=request.personality,
            industry_prompt=request.industry_prompt,
        )
        return {
            "prompt": prompt,
            "status": "success"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate prompt: {str(e)}")

