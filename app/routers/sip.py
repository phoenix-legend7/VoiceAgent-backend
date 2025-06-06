from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import httpx

from app.utils.httpx import get_httpx_headers, httpx_base_url
from app.schemas import AgentGet

router = APIRouter()

class CreateSipRequest(BaseModel):
    agent: AgentGet = None
    from_phone: str = None
    to_phone: str = None
    session_continuation: dict = None
    region: str = None

class CreateWebrtcOfferRequest(BaseModel):
    agent_id: str
    offer: dict = {
        "sdp": str,
        "type": str
    }

@router.post("/sip")
async def create_sip(create_sip_request: CreateSipRequest):
    try:
        agent = create_sip_request.agent.model_dump() if create_sip_request.agent else None
        data = {
            "init_agent": {
                "agent_id": agent.get("id") if agent else None,
                "agent_config": agent.get("config") if agent else None,
                "metadata": None,
                "include_metadata_in_prompt": None,
                "from_phone": create_sip_request.from_phone,
                "to_phone": create_sip_request.to_phone,
                "session_continuation": create_sip_request.session_continuation,
            },
            "region": create_sip_request.region
        }
        async with httpx.AsyncClient() as client:
            headers = get_httpx_headers()
            response = await client.post(f"{httpx_base_url}/sip", json=data, headers=headers)
            if response.status_code != 200 and response.status_code != 201:
                raise HTTPException(status_code=response.status_code, detail=response.text or "Unknown Error")
            return response.text

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/sip/{call_id}")
async def delete_sip(call_id: str):
    try:
        async with httpx.AsyncClient() as client:
            headers = get_httpx_headers()
            response = await client.delete(f"{httpx_base_url}/sip/{call_id}", headers=headers)
            if response.status_code != 200 and response.status_code != 201:
                raise HTTPException(status_code=response.status_code, detail=response.text or "Unknown Error")
            return response.text

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/webrtc/offer")
async def create_webrtc_offer(create_webrtc_offer_request: CreateWebrtcOfferRequest):
    """Create a WebRTC offer for a call."""
    try:
        async with httpx.AsyncClient() as client:
            headers = get_httpx_headers()
            response = await client.post(f"{httpx_base_url}/webrtc/offer", json=create_webrtc_offer_request.model_dump(), headers=headers)
            if response.status_code != 200 and response.status_code != 201:
                raise HTTPException(status_code=response.status_code, detail=response.text or "Unknown Error")
            return response.json()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
