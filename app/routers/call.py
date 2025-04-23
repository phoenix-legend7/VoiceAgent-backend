from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from io import BytesIO
import httpx

from app.utils.httpx import get_httpx_headers, httpx_base_url
from app.schemas import AgentGet

router = APIRouter()

class RegisterCallRequest(BaseModel):
    agent: AgentGet = None
    from_phone: str = None
    to_phone: str = None
    session_continuation: dict = None

class TerminateSessionRequest(BaseModel):
    message: str = None

class StartOutboundCallRequest(BaseModel):
    from_phone: str
    to_phone: str
    agent: AgentGet = None
    session_continuation: dict = None

@router.post("/register_call")
async def register_call(register_call_request: RegisterCallRequest):
    try:
        agent = register_call_request.agent.model_dump() if register_call_request.agent else None
        data = {
            "agent_id": agent.get("id") if agent else None,
            "agent_config": agent.get("config") if agent else None,
            "metadata": None,
            "include_metadata_in_prompt": None,
            "from_phone": register_call_request.from_phone,
            "to_phone": register_call_request.to_phone,
            "session_continuation": register_call_request.session_continuation
        }
        async with httpx.AsyncClient() as client:
            headers = get_httpx_headers()
            response = await client.post(f"{httpx_base_url}/register_call", json=data, headers=headers)

        return StreamingResponse(BytesIO(response.content), media_type=response.headers['Content-Type'])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/register_sip_call")
async def register_sip_call(register_sip_call_request: RegisterCallRequest):
    try:
        agent = register_sip_call_request.agent.model_dump() if register_sip_call_request.agent else None
        data = {
            "agent_id": agent.get("id") if agent else None,
            "agent_config": agent.get("config") if agent else None,
            "metadata": None,
            "include_metadata_in_prompt": None,
            "from_phone": register_sip_call_request.from_phone,
            "to_phone": register_sip_call_request.to_phone,
            "session_continuation": register_sip_call_request.session_continuation
        }
        async with httpx.AsyncClient() as client:
            headers = get_httpx_headers()
            response = await client.post(f"{httpx_base_url}/register_sip_call", json=data, headers=headers)

        return StreamingResponse(BytesIO(response.content), media_type=response.headers['Content-Type'])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sessions/{session_id}/terminate")
async def terminate_session(session_id: str, terminate_session_request: TerminateSessionRequest):
    try:
        async with httpx.AsyncClient() as client:
            headers = get_httpx_headers()
            response = await client.post(f"{httpx_base_url}/sessions/{session_id}/terminate", json=terminate_session_request.model_dump(), headers=headers)

        return StreamingResponse(BytesIO(response.content), media_type=response.headers['Content-Type'])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/start_outbound_call")
async def start_outbound_call(start_outbound_call_request: StartOutboundCallRequest):
    try:
        agent = start_outbound_call_request.agent.model_dump() if start_outbound_call_request.agent else None
        data = {
            "agent_id": agent.get("id") if agent else None,
            "agent_config": agent.get("config") if agent else None,
            "metadata": None,
            "include_metadata_in_prompt": None,
            "from_phone": start_outbound_call_request.from_phone,
            "to_phone": start_outbound_call_request.to_phone,
            "session_continuation": start_outbound_call_request.session_continuation
        }
        async with httpx.AsyncClient() as client:
            headers = get_httpx_headers()
            response = await client.post(f"{httpx_base_url}/start_outbound_call", json=data, headers=headers)

        return StreamingResponse(BytesIO(response.content), media_type=response.headers['Content-Type'])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
