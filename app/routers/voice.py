from fastapi import APIRouter, HTTPException
import httpx

from app.utils.httpx import get_httpx_headers, httpx_base_url

router = APIRouter()

@router.get("/custom")
async def voice(lang_code: str = "en"):
    async with httpx.AsyncClient() as client:
        try:
            headers = get_httpx_headers()
            response = await client.get(f"{httpx_base_url}/voices/custom", params={"lang_code": lang_code}, headers=headers)
            if response.status_code != 200 and response.status_code != 201:
                raise HTTPException(status_code=response.status_code, detail=response.text or "Unknown Error")
            return response.json()
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

@router.get("/")
async def get_voices(lang_code: str = "en"):
    async with httpx.AsyncClient() as client:
        try:
            headers = get_httpx_headers()
            response = await client.get(f"{httpx_base_url}/voices", params={"lang_code": lang_code}, headers=headers)
            if response.status_code != 200 and response.status_code != 201:
                raise HTTPException(status_code=response.status_code, detail=response.text or "Unknown Error")
            return response.json()
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
