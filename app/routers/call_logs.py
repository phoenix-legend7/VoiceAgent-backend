from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy import select, cast
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio
import httpx

from app.core.database import get_db, get_db_background
from app.models import Agent, CallLog
from app.routers.auth import current_active_user
# from app.utils.log import log_call_log
from app.utils.httpx import get_httpx_headers, httpx_base_url

router = APIRouter()

async def get_end_time():
    try:
        async with get_db_background() as session:
            response = await session.execute(
                select(CallLog.ts)
                .order_by(CallLog.ts.desc())
                .limit(1)
            )
            result = response.scalars().first()
            return result or 0
    except Exception as e:
        print(f"Real Time: Failed to get end time\n{str(e)}")
        return 0

async def get_next_cursor():
    try:
        async with get_db_background() as session:
            response = await session.execute(
                select(CallLog.ts)
                .order_by(CallLog.ts.asc())
                .limit(1)
            )
            result = response.scalars().first()
            return result or 0
    except Exception as e:
        print(f"Real Time: Failed to get next cursor\n{str(e)}")
        return 0

async def save_histories(histories: list):
    if not histories:
        return True
        
    try:
        async with get_db_background() as session:
            for history in histories:
                call_log = CallLog(
                    agent_id = history.get("agent_id") or None,
                    agent_config = history.get("agent_config") or None,
                    duration = history.get("duration") or None,
                    ts = history.get("ts") or None,
                    chat = history.get("chat") or None,
                    chars_used = history.get("chars_used") or None,
                    session_id = history.get("session_id") or None,
                    call_id = history.get("call_id") or None,
                    cost_breakdown = history.get("cost_breakdown") or None,
                    voip = history.get("voip") or None,
                    recording = history.get("recording") or None,
                    call_metadata = history.get("metadata") or None,
                    function_calls = history.get("function_calls") or None,
                    call_status = history.get("call_status") or None,
                )
                session.add(call_log)
            try:
                await session.commit()
            except Exception as e:
                print(f"Real Time: Failed to save history\n{str(e)}")
                await session.rollback()
                return False
            return True
    except Exception as e:
        print(f"Real Time: Failed to save call logs\n{str(e)}")
        return False

async def get_all_logs():
    await asyncio.sleep(10)  # Initial delay
    max_ts = await get_next_cursor()
    
    while True:
        try:
            print('-------------------------')
            print(f"Next cursor is {max_ts}")
            
            async with httpx.AsyncClient() as client:
                headers = get_httpx_headers()
                params = {
                    "limit": 100,
                    "start_after_ts": max_ts,
                }
                response = await client.get(f"{httpx_base_url}/call-logs", headers=headers, params=params)
                if response.status_code != 200 and response.status_code != 201:
                    raise Exception(response.text or "Unknown Error")
                    
                data = response.json()
                histories = data.get("histories", [])
                print(f"{len(histories)} histories found")
                
                if histories:
                    success = await save_histories(histories)
                    if not success:
                        await asyncio.sleep(5)  # Wait before retrying on failure
                        continue
                
                print('-------------------------')
                max_ts = data.get("next_cursor", 0)
                if not max_ts:
                    print("No more data")
                    break
                    
                await asyncio.sleep(1)  # Small delay between batches

        except Exception as e:
            print(f"Real Time: Failed to get all call logs\n{str(e)}")
            await asyncio.sleep(10)

async def get_next_logs():
    last_time = await get_end_time()
    try:
        if not last_time:
            print("No data updated")
            return
            
        start_time = last_time + 1
        print('-------------------------')
        print(f"Start time is {start_time}")
        
        async with httpx.AsyncClient() as client:
            headers = get_httpx_headers()
            params = {
                "limit": 100,
                "start_time": start_time,
            }
            response = await client.get(f"{httpx_base_url}/call-logs", headers=headers, params=params)
            if response.status_code != 200 and response.status_code != 201:
                raise Exception(response.text or "Unknown Error")
                
            data = response.json()
            histories = data.get("histories", [])
            if not histories:
                print("No data updated")
                return
                
            print(f"{len(histories)} new histories found")
            await save_histories(histories)

    except Exception as e:
        print(f"Real Time: Failed to get next call logs\n{str(e)}")

@router.get("/")
async def get_logs(
    limit: int = Query(20, description='Number of records to return per page. Max 100.', ge=1, le=100),
    start_after_ts: float = None,
    agent_id: str = None,
    call_status: str = None,
    phone_number: str = None,
    start_time: float = None,
    end_time: float = None,
    db: AsyncSession = Depends(get_db),
    user = Depends(current_active_user)
):
    try:
        query = (
            select(CallLog)
            .join(Agent, CallLog.agent_id == Agent.id)  # join so we can filter by user
            .where(Agent.user_id == user.id)            # filter to current user
        )
        if start_after_ts:
            query = query.where(CallLog.ts <= start_after_ts)
        if agent_id:
            query = query.where(CallLog.agent_id == agent_id)
        if call_status:
            query = query.where(CallLog.call_status == call_status)
        if phone_number:
            query = query.where(CallLog.voip.op("@>")(cast([{"to": phone_number}], JSONB)))
        if start_time:
            query = query.where(CallLog.ts >= start_time)
        if end_time:
            query = query.where(CallLog.ts <= end_time)
        query = query.order_by(CallLog.ts.desc()).limit(limit)
        
        result = await db.execute(query)
        return result.scalars().all()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{session_id}")
async def get_call_log(session_id: str, db: AsyncSession = Depends(get_db), _ = Depends(current_active_user)):
    try:
        result = await db.execute(select(CallLog).where(CallLog.session_id == session_id))
        log = result.scalar_one_or_none()
        if not log:
            raise HTTPException(status_code=404, detail=f"Log {session_id} not found.")
        return log

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{session_id}")
async def delete_call_log(session_id: str, db: AsyncSession = Depends(get_db), _ = Depends(current_active_user)):
    try:
        async with httpx.AsyncClient() as client:
            headers = get_httpx_headers()
            response = await client.delete(f"{httpx_base_url}/call-logs/{session_id}", headers=headers)
            if response.status_code != 200 and response.status_code != 201:
                raise HTTPException(status_code=response.status_code, detail=response.text or "Unknown Error")
            result = await db.execute(select(CallLog).where(CallLog.session_id == session_id))
            log = result.scalar_one_or_none()
            if log:
                try:
                    await db.delete(log)
                    await db.commit()
                except Exception as e:
                    await db.rollback()
            return response.text

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
