from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from io import BytesIO
import httpx

from app.utils.httpx import get_httpx_headers, httpx_base_url

router = APIRouter()

class SetPhoneAgentRequest(BaseModel):
    phone: str
    agent_id: str = None

@router.post("/set_phone_agent")
async def set_phone_agent(set_phone_agent_request: SetPhoneAgentRequest):
    try:
        async with httpx.AsyncClient() as client:
            headers = get_httpx_headers()
            response = await client.post(f"{httpx_base_url}/set_phone_agent", json=set_phone_agent_request.model_dump(), headers=headers)

        return StreamingResponse(BytesIO(response.content), media_type=response.headers['Content-Type'])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/phones")
async def get_phones():
    try:
        async with httpx.AsyncClient() as client:
            headers = get_httpx_headers()
            response = await client.get(f"{httpx_base_url}/phones", headers=headers)

        return StreamingResponse(BytesIO(response.content), media_type=response.headers['Content-Type'])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/phone/{phone_id}")
async def get_phone(phone_id: str):
    try:
        async with httpx.AsyncClient() as client:
            headers = get_httpx_headers()
            response = await client.get(f"{httpx_base_url}/phone/{phone_id}", headers=headers)

        return StreamingResponse(BytesIO(response.content), media_type=response.headers['Content-Type'])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
