from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from io import BytesIO
import httpx

from app.utils.httpx import get_httpx_headers, httpx_base_url

router = APIRouter()

class CreateCampaignRequest(BaseModel):
    name: str

class UploadCampaignRecordRequest(BaseModel):
    phone: str
    metadata: dict = None

class SetCallerRequest(BaseModel):
    caller: str

@router.post("/")
async def create_campaign(create_campaign_request: CreateCampaignRequest):
    try:
        async with httpx.AsyncClient() as client:
            headers = get_httpx_headers()
            response = await client.post(f"{httpx_base_url}/campaigns", json=create_campaign_request.model_dump(), headers=headers)

        return StreamingResponse(BytesIO(response.content), media_type=response.headers['Content-Type'])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/")
async def get_campaigns():
    try:
        async with httpx.AsyncClient() as client:
            headers = get_httpx_headers()
            response = await client.get(f"{httpx_base_url}/campaigns", headers=headers)

        return StreamingResponse(BytesIO(response.content), media_type=response.headers['Content-Type'])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{campaign_id}/records")
async def upload_campaign_record(campaign_id: str, upload_campaign_record_request: UploadCampaignRecordRequest):
    try:
        async with httpx.AsyncClient() as client:
            headers = get_httpx_headers()
            response = await client.post(f"{httpx_base_url}/campaigns/{campaign_id}/records", json=upload_campaign_record_request.model_dump(), headers=headers)

        return StreamingResponse(BytesIO(response.content), media_type=response.headers['Content-Type'])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{campaign_id}/set_caller")
async def set_caller(campaign_id: str, set_caller_request: SetCallerRequest):
    try:
        async with httpx.AsyncClient() as client:
            headers = get_httpx_headers()
            response = await client.post(f"{httpx_base_url}/campaigns/{campaign_id}/set_caller", json=set_caller_request.model_dump(), headers=headers)

        return StreamingResponse(BytesIO(response.content), media_type=response.headers['Content-Type'])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{campaign_id}/start")
async def start_campaign(campaign_id: str):
    try:
        async with httpx.AsyncClient() as client:
            headers = get_httpx_headers()
            response = await client.post(f"{httpx_base_url}/campaigns/{campaign_id}/start", headers=headers)

        return StreamingResponse(BytesIO(response.content), media_type=response.headers['Content-Type'])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{campaign_id}/stop")
async def stop_campaign(campaign_id: str):
    try:
        async with httpx.AsyncClient() as client:
            headers = get_httpx_headers()
            response = await client.post(f"{httpx_base_url}/campaigns/{campaign_id}/stop", headers=headers)

        return StreamingResponse(BytesIO(response.content), media_type=response.headers['Content-Type'])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{campaign_id}")
async def get_campaign(campaign_id: str):
    try:
        async with httpx.AsyncClient() as client:
            headers = get_httpx_headers()
            response = await client.get(f"{httpx_base_url}/campaigns/{campaign_id}", headers=headers)

        return StreamingResponse(BytesIO(response.content), media_type=response.headers['Content-Type'])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{campaign_id}")
async def delete_campaign(campaign_id: str):
    try:
        async with httpx.AsyncClient() as client:
            headers = get_httpx_headers()
            response = await client.delete(f"{httpx_base_url}/campaigns/{campaign_id}", headers=headers)

        return StreamingResponse(BytesIO(response.content), media_type=response.headers['Content-Type'])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
