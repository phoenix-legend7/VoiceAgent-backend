from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import select, cast, Text
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone
import httpx

from app.core.database import get_db
from app.models import Agent
from app.routers.auth import current_active_user
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
async def create_sip(
    create_sip_request: CreateSipRequest,
    db: AsyncSession = Depends(get_db),
    user = Depends(current_active_user)
):
    try:
        agent = create_sip_request.agent.model_dump() if create_sip_request.agent else None
        if not agent:
            raise HTTPException(status_code=400, detail="Agent is missing")
        agent_id = agent.get("id")
        result = await db.execute(select(Agent).where(Agent.id == agent_id, Agent.user_id == user.id))
        db_agent = result.scalar_one_or_none()
        if not db_agent:
            raise HTTPException(status_code=404, detail=f"Not found agent {agent_id}")
        data = {
            "init_agent": {
                "agent_id": agent_id,
                "agent_config": agent.get("config"),
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
            data = response.json()
            sip = db_agent.sip or dict()
            sip[data.get("sip")] = datetime.now(timezone.utc).timestamp()
            db_agent.sip = sip
            try:
                await db.commit()
                await db.refresh(db_agent)
            except Exception as e:
                print(f"Failed to update agent: {str(e)}")
            return data

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/sip/{call_id}")
async def delete_sip(call_id: str, db: AsyncSession = Depends(get_db), user = Depends(current_active_user)):
    try:
        result = await db.execute(select(Agent).where(Agent.user_id == user.id, cast(Agent.sip, Text).contains(call_id)))
        db_agent = result.scalar_one_or_none()
        if not db_agent:
            raise HTTPException(status_code=404, detail=f"Not found call {call_id}")
        async with httpx.AsyncClient() as client:
            headers = get_httpx_headers()
            response = await client.delete(f"{httpx_base_url}/sip/{call_id}", headers=headers)
            if response.status_code != 200 and response.status_code != 201:
                raise HTTPException(status_code=response.status_code, detail=response.text or "Unknown Error")
            db_agent.sip = {k: v for k, v in db_agent.sip.items() if call_id not in k}
            try:
                await db.commit()
                await db.refresh(db_agent)
            except Exception as e:
                print(f"Failed to update agent: {str(e)}")
            return response.text

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/webrtc/offer")
async def create_webrtc_offer(create_webrtc_offer_request: CreateWebrtcOfferRequest, _ = Depends(current_active_user)):
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
