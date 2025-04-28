from fastapi import APIRouter, HTTPException
import httpx

from app.utils.httpx import get_httpx_headers, httpx_base_url

router = APIRouter()

@router.get("/{session_id}")
async def get_call_log(session_id: str):
    try:
        async with httpx.AsyncClient() as client:
            headers = get_httpx_headers()
            response = await client.get(f"{httpx_base_url}/call-logs/{session_id}", headers=headers)
            return response.json()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{session_id}")
async def delete_call_log(session_id: str):
    try:
        async with httpx.AsyncClient() as client:
            headers = get_httpx_headers()
            response = await client.delete(f"{httpx_base_url}/call-logs/{session_id}", headers=headers)
            return response.json()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


