from fastapi import APIRouter, HTTPException
import httpx

from app.utils.httpx import get_httpx_headers, httpx_base_url

router = APIRouter()

@router.get("/")
async def get_logs(
    limit: int = 20,
    start_after_ts: float = None,
    agent_id: str = None,
    call_status: str = None,
    phone_number: str = None,
    start_time: int = None,
    end_time: int = None
):
    try:
        async with httpx.AsyncClient() as client:
            headers = get_httpx_headers()
            params = {"limit": limit}
            if start_after_ts:
                params["start_after_ts"] = start_after_ts
            if agent_id:
                params["agent_id"] = agent_id
            if call_status:
                params["call_status"] = call_status
            if phone_number:
                params["phone_number"] = phone_number
            if start_time:
                params["start_time"] = start_time
            if end_time:
                params["end_time"] = end_time

            response = await client.get(f"{httpx_base_url}/call-logs", headers=headers, params=params)
            if response.status_code != 200 and response.status_code != 201:
                raise HTTPException(status_code=response.status_code, detail=response.text or "Unknown Error")
            return response.json()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{session_id}")
async def get_call_log(session_id: str):
    try:
        async with httpx.AsyncClient() as client:
            headers = get_httpx_headers()
            response = await client.get(f"{httpx_base_url}/call-logs/{session_id}", headers=headers)
            if response.status_code != 200 and response.status_code != 201:
                raise HTTPException(status_code=response.status_code, detail=response.text or "Unknown Error")
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
            if response.status_code != 200 and response.status_code != 201:
                raise HTTPException(status_code=response.status_code, detail=response.text or "Unknown Error")
            return response.text

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


