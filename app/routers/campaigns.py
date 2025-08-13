from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import httpx

from app.core.database import get_db
from app.models import Campaign
from app.routers.auth import current_active_user
from app.utils.httpx import get_httpx_headers, httpx_base_url

router = APIRouter()

class CreateCampaignRequest(BaseModel):
    name: str

class UpdateCampaignRequest(BaseModel):
    name: str = None
    include_metadata_in_prompt: bool = None

class SetCallerRequest(BaseModel):
    caller: str

async def get_campaigns():
    try:
        async with httpx.AsyncClient() as client:
            headers = get_httpx_headers()
            response = await client.get(f"{httpx_base_url}/campaigns", headers=headers)
            if response.status_code != 200 and response.status_code != 201:
                raise HTTPException(status_code=response.status_code, detail=response.text or "Unknown Error")
            return response.json()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/")
async def create_campaign(
    create_campaign_request: CreateCampaignRequest,
    db: AsyncSession = Depends(get_db),
    user = Depends(current_active_user)
):
    try:
        async with httpx.AsyncClient() as client:
            headers = get_httpx_headers()
            response = await client.post(f"{httpx_base_url}/campaigns", json=create_campaign_request.model_dump(), headers=headers)
            if response.status_code != 200 and response.status_code != 201:
                raise HTTPException(status_code=response.status_code, detail=response.text or "Unknown Error")
            data = response.json()
            db_campaign = Campaign(
                id = data.get("id"),
                name = create_campaign_request.name,
                status = data.get("status"),
                records = data.get("records"),
                created_at = data.get("created_at"),
                user_id = user.id,
            )
            db.add(db_campaign)
            try:
                await db.commit()
                await db.refresh(db_campaign)
            except Exception as e:
                print(f"Error while saving campaign: {str(e)}")
            return data

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/")
async def get_campaigns_db(db: AsyncSession = Depends(get_db), user = Depends(current_active_user)):
    try:
        result = await db.execute(select(Campaign).where(Campaign.user_id == user.id))
        return result.scalars().all()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{campaign_id}/records")
async def upload_campaign_record(
    campaign_id: str,
    upload_campaign_record_request: list[dict],
    db: AsyncSession = Depends(get_db),
    user = Depends(current_active_user)
):
    result = await db.execute(select(Campaign).where(Campaign.id == campaign_id, Campaign.user_id == user.id))
    db_campaign = result.scalar_one_or_none()
    if not db_campaign:
        raise HTTPException(status_code=404, detail=f"Not found campaign {campaign_id}")
    try:
        async with httpx.AsyncClient() as client:
            headers = get_httpx_headers()
            response = await client.post(f"{httpx_base_url}/campaigns/{campaign_id}/records", json=upload_campaign_record_request, headers=headers)
            if response.status_code != 200 and response.status_code != 201:
                raise HTTPException(status_code=response.status_code, detail=response.text or "Unknown Error")
            records = {record["phone"]: record for record in db_campaign.records}
            for record in upload_campaign_record_request:
                if record["phone"] not in records:
                    records[record["phone"]] = record
            db_campaign.records = list(records.values())
            try:
                await db.commit()
                await db.refresh(db_campaign)
            except Exception as e:
                print(f"Failed to update campaign: {str(e)}")
            return response.text

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{campaign_id}/set_caller")
async def set_caller(
    campaign_id: str,
    set_caller_request: SetCallerRequest,
    db: AsyncSession = Depends(get_db),
    user = Depends(current_active_user)
):
    result = await db.execute(select(Campaign).where(Campaign.id == campaign_id, Campaign.user_id == user.id))
    db_campaign = result.scalar_one_or_none()
    if not db_campaign:
        raise HTTPException(status_code=404, detail=f"Not found campaign {campaign_id}")
    try:
        async with httpx.AsyncClient() as client:
            headers = get_httpx_headers()
            response = await client.post(f"{httpx_base_url}/campaigns/{campaign_id}/set_caller", json=set_caller_request.model_dump(), headers=headers)
            if response.status_code != 200 and response.status_code != 201:
                raise HTTPException(status_code=response.status_code, detail=response.text or "Unknown Error")
            db_campaign.caller = set_caller_request.caller
            try:
                await db.commit()
                await db.refresh(db_campaign)
            except Exception as e:
                print(f"Failed to update campaign: {str(e)}")
            return response.text

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{campaign_id}/start")
async def start_campaign(campaign_id: str, _ = Depends(current_active_user)):
    try:
        async with httpx.AsyncClient() as client:
            headers = get_httpx_headers()
            response = await client.post(f"{httpx_base_url}/campaigns/{campaign_id}/start", headers=headers)
            if response.status_code != 200 and response.status_code != 201:
                raise HTTPException(status_code=response.status_code, detail=response.text or "Unknown Error")
            return response.text

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{campaign_id}/stop")
async def stop_campaign(campaign_id: str, _ = Depends(current_active_user)):
    try:
        async with httpx.AsyncClient() as client:
            headers = get_httpx_headers()
            response = await client.post(f"{httpx_base_url}/campaigns/{campaign_id}/stop", headers=headers)
            if response.status_code != 200 and response.status_code != 201:
                raise HTTPException(status_code=response.status_code, detail=response.text or "Unknown Error")
            return response.text

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{campaign_id}")
async def get_campaign(
    campaign_id: str,
    db: AsyncSession = Depends(get_db),
    user = Depends(current_active_user)
):
    try:
        result = await db.execute(select(Campaign).where(Campaign.id == campaign_id, Campaign.user_id == user.id))
        db_campaign = result.scalar_one_or_none()
        if not db_campaign:
            raise HTTPException(status_code=404, detail=f"Not found campaign {campaign_id}")
        return db_campaign
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{campaign_id}")
async def delete_campaign(
    campaign_id: str,
    db: AsyncSession = Depends(get_db),
    user = Depends(current_active_user)
):
    result = await db.execute(select(Campaign).where(Campaign.id == campaign_id, Campaign.user_id == user.id))
    db_campaign = result.scalar_one_or_none()
    if not db_campaign:
        raise HTTPException(status_code=404, detail=f"Not found campaign {campaign_id}")

    try:
        async with httpx.AsyncClient() as client:
            headers = get_httpx_headers()
            response = await client.delete(f"{httpx_base_url}/campaigns/{campaign_id}", headers=headers)
            if response.status_code != 200 and response.status_code != 201:
                raise HTTPException(status_code=response.status_code, detail=response.text or "Unknown Error")
            try:
                await db.delete(db_campaign)
                await db.commit()
                await db.refresh(db_campaign)
            except Exception as e:
                print(f"Failed to delete campaign: {str(e)}")
            return response.text

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# @router.get("/{campaign_id}/info")
async def get_campaign_info(campaign_id: str):
    try:
        async with httpx.AsyncClient() as client:
            headers = get_httpx_headers()
            response = await client.get(f"{httpx_base_url}/campaigns/{campaign_id}/info", headers=headers)
            if response.status_code != 200 and response.status_code != 201:
                raise HTTPException(status_code=response.status_code, detail=response.text or "Unknown Error")
            return response.json()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{campaign_id}/info")
async def update_campaign_info(
    campaign_id: str,
    request: UpdateCampaignRequest,
    db: AsyncSession = Depends(get_db),
    user = Depends(current_active_user)
):
    result = await db.execute(select(Campaign).where(Campaign.id == campaign_id, Campaign.user_id == user.id))
    db_campaign = result.scalar_one_or_none()
    if not db_campaign:
        raise HTTPException(status_code=404, detail=f"Not found campaign {campaign_id}")

    try:
        async with httpx.AsyncClient() as client:
            headers = get_httpx_headers()
            response = await client.put(f"{httpx_base_url}/campaigns/{campaign_id}/info", json=request.model_dump(), headers=headers)
            if response.status_code != 200 and response.status_code != 201:
                raise HTTPException(status_code=response.status_code, detail=response.text or "Unknown Error")
            if request.include_metadata_in_prompt != None:
                db_campaign.include_metadata_in_prompt = request.include_metadata_in_prompt
            if request.name != None:
                db_campaign.name = request.name
            try:
                await db.commit()
                await db.refresh(db_campaign)
            except Exception as e:
                print(f"Failed to update campaign: {str(e)}")
            return response.json()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{campaign_id}/records/{phone}")
async def delete_campaign_record(
    campaign_id: str,
    phone: str,
    db: AsyncSession = Depends(get_db),
    user = Depends(current_active_user)
):
    result = await db.execute(select(Campaign).where(Campaign.id == campaign_id, Campaign.user_id == user.id))
    db_campaign = result.scalar_one_or_none()
    if not db_campaign:
        raise HTTPException(status_code=404, detail=f"Not found campaign {campaign_id}")

    try:
        async with httpx.AsyncClient() as client:
            headers = get_httpx_headers()
            response = await client.delete(f"{httpx_base_url}/campaigns/{campaign_id}/records/{phone}", headers=headers)
            if response.status_code != 200 and response.status_code != 201:
                raise HTTPException(status_code=response.status_code, detail=response.text or "Unknown Error")
            records = {record["phone"]: record for record in db_campaign.records}
            if phone in records:
                records.pop(phone)
            db_campaign.records = list(records.values())
            try:
                await db.commit()
                await db.refresh(db_campaign)
            except Exception as e:
                print(f"Failed to update campaign: {str(e)}")
            return response.text

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
