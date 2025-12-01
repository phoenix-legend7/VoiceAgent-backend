from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone
import httpx

from app.core.database import get_db
from app.models import Phone, User
from app.routers.auth import current_active_user
from app.utils.httpx import get_httpx_headers, httpx_base_url

router = APIRouter()

class SetPhoneAgentRequest(BaseModel):
    phone: str
    agent_id: str = None

class SetAgentRequest(BaseModel):
    agent_id: str

class ImportPhoneRequest(BaseModel):
    provider: str
    region: str
    country: str
    phone: str
    api_key: str = None
    api_secret: str = None
    account_sid: str = None
    app_id: str = None
    subdomain: str = None
    auth_id: str = None
    auth_token: str = None

class PurchasePhoneRequest(BaseModel):
    country: str
    area_code: str
    street: str = None
    city: str = None
    state_region: str = None
    postal_code: str = None

class SetTaggingRequest(BaseModel):
    tags: list[str]

@router.post("/set_phone_agent")
async def set_phone_agent(
    set_phone_agent_request: SetPhoneAgentRequest,
    db: AsyncSession = Depends(get_db),
    user = Depends(current_active_user)
):
    try:
        phone = set_phone_agent_request.phone
        result = await db.execute(select(Phone).where(Phone.id == phone, Phone.user_id == user.id))
        db_phone = result.scalar_one_or_none()
        if not db_phone:
            raise HTTPException(status_code=404, detail=f"Not found phone {phone}")
        async with httpx.AsyncClient() as client:
            headers = get_httpx_headers()
            response = await client.post(f"{httpx_base_url}/set_phone_agent", json=set_phone_agent_request.model_dump(), headers=headers)
            if response.status_code != 200 and response.status_code != 201:
                raise HTTPException(status_code=response.status_code, detail=response.text or "Unknown Error")
            db_phone.agent_id = set_phone_agent_request.agent_id
            try:
                await db.commit()
                await db.refresh(db_phone)
            except Exception as e:
                print(f"Error while setting agent: {str(e)}")
            return response.text

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# @router.get("/phones")
async def get_phones():
    try:
        async with httpx.AsyncClient() as client:
            headers = get_httpx_headers()
            response = await client.get(f"{httpx_base_url}/phones", headers=headers)
            if response.status_code != 200 and response.status_code != 201:
                raise HTTPException(status_code=response.status_code, detail=response.text or "Unknown Error")
            return response.json()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# @router.get("/phone/{phone_id}")
async def get_phone(phone_id: str):
    try:
        async with httpx.AsyncClient() as client:
            headers = get_httpx_headers()
            response = await client.get(f"{httpx_base_url}/phones/{phone_id}", headers=headers)
            if response.status_code != 200 and response.status_code != 201:
                raise HTTPException(status_code=response.status_code, detail=response.text or "Unknown Error")
            return response.json()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/phones")
async def get_phones_db(db: AsyncSession = Depends(get_db), user = Depends(current_active_user)):
    try:
        result = await db.execute(select(Phone).where(Phone.user_id == user.id))
        db_phone = result.scalars().all()
        return db_phone
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/phone/{phone_id}")
async def get_phone_db(
    phone_id: str,
    db: AsyncSession = Depends(get_db),
    user = Depends(current_active_user)
):
    try:
        result = await db.execute(select(Phone).where(Phone.id == phone_id, Phone.user_id == user.id))
        db_phone = result.scalar_one_or_none()
        if not db_phone:
            raise HTTPException(status_code=404, detail=f"Not found phone {phone_id}")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/phone/{phone_id}")
async def delete_phone(
    phone_id: str,
    db: AsyncSession = Depends(get_db),
    user = Depends(current_active_user)
):
    try:
        result = await db.execute(select(Phone).where(Phone.id == phone_id, Phone.user_id == user.id))
        db_phone = result.scalar_one_or_none()
        if not db_phone:
            raise HTTPException(status_code=404, detail=f"Not found phone {phone_id}")
        async with httpx.AsyncClient() as client:
            headers = get_httpx_headers()
            response = await client.delete(f"{httpx_base_url}/phones/{phone_id}", headers=headers)
            if response.status_code != 200 and response.status_code != 201:
                raise HTTPException(status_code=response.status_code, detail=response.text or "Unknown Error")
            try:
                await db.delete(db_phone)
                await db.commit()
                await db.refresh(db_phone)
            except Exception as e:
                print(f"Error while setting agent config: {str(e)}")
            return {"detail": "Phone deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/phone/{phone_id}/tags")
async def set_phone_tag(
    phone_id: str,
    request: SetTaggingRequest,
    db: AsyncSession = Depends(get_db),
    user = Depends(current_active_user)
):
    try:
        result = await db.execute(select(Phone).where(Phone.id == phone_id, Phone.user_id == user.id))
        db_phone = result.scalar_one_or_none()
        if not db_phone:
            raise HTTPException(status_code=404, detail=f"Not found phone {phone_id}")
        async with httpx.AsyncClient() as client:
            headers = get_httpx_headers()
            response = await client.put(f"{httpx_base_url}/phones/{phone_id}", json=request.model_dump(), headers=headers)
            if response.status_code != 200 and response.status_code != 201:
                raise HTTPException(status_code=response.status_code, detail=response.text or "Unknown Error")
            db_phone.tags = request.tags
            try:
                await db.commit()
                await db.refresh(db_phone)
            except Exception as e:
                print(f"Error while setting agent config: {str(e)}")
            return response.text

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/phones/{phone}/agent-config-override")
async def set_agent_config_override(
    phone: str,
    agent_config_override: dict,
    db: AsyncSession = Depends(get_db),
    user = Depends(current_active_user)
):
    try:
        result = await db.execute(select(Phone).where(Phone.id == phone, Phone.user_id == user.id))
        db_phone = result.scalar_one_or_none()
        if not db_phone:
            raise HTTPException(status_code=404, detail=f"Not found phone {phone}")
        async with httpx.AsyncClient() as client:
            headers = get_httpx_headers()
            response = await client.post(f"{httpx_base_url}/phones/{phone}/agent-config-override", json=agent_config_override, headers=headers)
            if response.status_code != 200 and response.status_code != 201:
                raise HTTPException(status_code=response.status_code, detail=response.text or "Unknown Error")
            db_phone.agent_config_override = agent_config_override
            try:
                await db.commit()
                await db.refresh(db_phone)
            except Exception as e:
                print(f"Error while setting agent config: {str(e)}")
            return response.text

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/phones/{phone}/set_agent")
async def set_agent(
    phone: str,
    request: SetAgentRequest,
    db: AsyncSession = Depends(get_db),
    user = Depends(current_active_user)
):
    try:
        result = await db.execute(select(Phone).where(Phone.id == phone, Phone.user_id == user.id))
        db_phone = result.scalar_one_or_none()
        if not db_phone:
            raise HTTPException(status_code=404, detail=f"Not found phone {phone}")
        async with httpx.AsyncClient() as client:
            headers = get_httpx_headers()
            response = await client.post(f"{httpx_base_url}/phones/{phone}/set_agent", json=request.model_dump(), headers=headers)
            if response.status_code != 200 and response.status_code != 201:
                raise HTTPException(status_code=response.status_code, detail=response.text or "Unknown Error")
            db_phone.agent_id = request.agent_id
            try:
                await db.commit()
                await db.refresh(db_phone)
            except Exception as e:
                print(f"Error while setting agent: {str(e)}")
            return response.text

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/phones/import")
async def import_phone_number(
    request: ImportPhoneRequest,
    db: AsyncSession = Depends(get_db),
    user = Depends(current_active_user)
):
    try:
        async with httpx.AsyncClient() as client:
            headers = get_httpx_headers()
            payload = {
                "country": request.country,
                "phone": request.phone,
                "provider": request.provider,
                "region": request.region,
            }
            if request.subdomain:
                payload["subdomain"] = request.subdomain
            if request.auth_id:
                payload["auth_id"] = request.auth_id
            if request.auth_token:
                payload["auth_token"] = request.auth_token
            if request.api_key:
                payload["api_key"] = request.api_key
            if request.api_secret:
                payload["api_secret"] = request.api_secret
            if request.account_sid:
                payload["account_sid"] = request.account_sid
            if request.app_id:
                payload["app_id"] = request.app_id
            response = await client.post(f"{httpx_base_url}/phones/import", json=payload, headers=headers)
            if response.status_code != 200 and response.status_code != 201:
                raise HTTPException(status_code=response.status_code, detail=response.text or "Unknown Error")
            db_phone = Phone(
                id = request.phone,
                created_at = int(datetime.now(timezone.utc).timestamp()),
                user_id = user.id,
                country = request.country,
                provider = request.provider,
                region = request.region,
                api_key = request.api_key,
                api_secret = request.api_secret,
                account_sid = request.account_sid,
                app_id = request.app_id,
                subdomain = request.subdomain,
                auth_id = request.auth_id,
                auth_token = request.auth_token,
            )
            db.add(db_phone)
            try:
                await db.commit()
                await db.refresh(db_phone)
            except Exception as e:
                print(f"Error while saving phone: {str(e)}")
            return response.text

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/phones/purchase")
async def purchase_phone_number(
    request: PurchasePhoneRequest,
    db: AsyncSession = Depends(get_db),
    user = Depends(current_active_user)
):
    try:
        remain_credit = user.total_credit - user.used_credit
        if remain_credit < 3000:
            raise HTTPException(status_code=400, detail="You don't have enough credit")
        async with httpx.AsyncClient() as client:
            headers = get_httpx_headers()
            response = await client.post(f"{httpx_base_url}/phones/purchase", json=request.model_dump(), headers=headers)
            if response.status_code != 200 and response.status_code != 201:
                raise HTTPException(status_code=response.status_code, detail=response.text or "Unknown Error")
            phone_number = response.text
            db_phone = Phone(
                id = phone_number,
                created_at = int(datetime.now(timezone.utc).timestamp()),
                user_id = user.id,
                country = request.country,
                area_code = request.area_code,
                street = request.street,
                city = request.city,
                state_region = request.state_region,
                postal_code = request.postal_code,
            )
            db.add(db_phone)
            # Increment user's used credit after successful purchase
            try:
                result = await db.execute(select(User).where(User.id == user.id))
                db_user = result.scalar_one_or_none()
                if db_user:
                    db_user.used_credit = (db_user.used_credit or 0) + 300
            except Exception as e:
                print(f"Error while updating user credit: {str(e)}")
            try:
                await db.commit()
                await db.refresh(db_phone)
            except Exception as e:
                print(f"Error while saving phone: {str(e)}")
            return phone_number

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
