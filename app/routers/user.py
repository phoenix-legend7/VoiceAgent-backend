from fastapi import APIRouter, HTTPException, Depends
import httpx

from app.routers.auth import current_active_user
from app.utils.httpx import get_httpx_headers, httpx_base_url

router = APIRouter()

async def get_user_info():
    try:
        async with httpx.AsyncClient() as client:
            headers = get_httpx_headers()
            response = await client.get(f"{httpx_base_url}/user/info", headers=headers)
            if response.status_code != 200 and response.status_code != 201:
                raise HTTPException(status_code=response.status_code, detail=response.text or "Unknown Error")
            return response.json()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
