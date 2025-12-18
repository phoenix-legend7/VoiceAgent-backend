from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone, timedelta
import itertools

from app.core.database import get_db
from app.models import Agent, CallLog
from app.routers.agent import get_agents
from app.routers.auth import current_active_user

router = APIRouter()

def is_success(row: CallLog):
    error_statuses = ['timeout', 'busy', 'no-answer', 'failed', 'canceled', 'error', 'unknown']
    return not row.call_status in error_statuses

def is_qualified(row: CallLog):
    statuses = ["in-progress", "user-ended", "agent-ended", "api-ended", "chat_completion"]
    return row.call_status in statuses

def is_answering(row: CallLog):
    statuses = ["voicemail-hangup", "voicemail-message"]
    return row.call_status in statuses

def is_no_answer(row: CallLog):
    statuses = ["no-answer", "timeout", "canceled"]
    return row.call_status in statuses

def is_busy(row: CallLog):
    return row.call_status == "busy"

def group_by_agent(rows):
    grouped = {}
    get_key = lambda x: x.agent_id  # Pre-compute key accessor
    for row in rows:
        k = get_key(row)
        lst = grouped.get(k)
        if lst is None:
            lst = []
            grouped[k] = lst
        lst.append(row)
    return grouped

def calc_total_minutes(rows):
    return sum([row.duration or 0 for row in rows]) / 60

def calc_total_cost(rows):
    return sum(
        item.get("credit", 0) 
        for item in itertools.chain.from_iterable(
            d.cost_breakdown if d.cost_breakdown is not None else [] 
            for d in rows
        )
    )

def calc_success_logs(rows):
    return len([row for row in rows if is_success(row)])

@router.get("/")
async def get_dashboard_data(
    agent_id: str = None,
    time_period: str = "today", # today, week, month, quarter
    db: AsyncSession = Depends(get_db),
    user = Depends(current_active_user)
):
    try:
        # Query agents for the current user
        agents_result = await db.execute(select(Agent).where(Agent.user_id == user.id))
        agents = [{"id": agent.id, "name": agent.name} for agent in agents_result.scalars().all()]
        
        query = (
            select(CallLog)
            .join(Agent, CallLog.agent_id == Agent.id)  # join so we can filter by user
            .where(Agent.user_id == user.id)            # filter to current user
        )
        if agent_id:
            query = query.where(CallLog.agent_id == agent_id)
        if time_period:
            now = datetime.now(timezone.utc)
            if time_period == 'today':
                start_time = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
                end_time = start_time + timedelta(days=1)
            elif time_period == 'week':
                start_time = now - timedelta(days=now.weekday())
                start_time = datetime(start_time.year, start_time.month, start_time.day, tzinfo=timezone.utc)
                end_time = start_time + timedelta(days=7)
            elif time_period == 'month':
                start_time = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
                if now.month == 12:
                    end_time = datetime(now.year + 1, 1, 1, tzinfo=timezone.utc)
                else:
                    end_time = datetime(now.year, now.month + 1, 1, tzinfo=timezone.utc)
            elif time_period == 'quarter':
                quarter_start_month = ((now.month - 1) // 3) * 3 + 1
                start_time = datetime(now.year, quarter_start_month, 1, tzinfo=timezone.utc)
                if quarter_start_month == 10:
                    end_time = datetime(now.year + 1, 1, 1, tzinfo=timezone.utc)
                else:
                    end_time = datetime(now.year, quarter_start_month + 3, 1, tzinfo=timezone.utc)
            else:
                raise HTTPException(status_code=400, detail="Invalid time period. Must be one of: today, week, month, quarter")

            query = query.where(CallLog.ts >= start_time.timestamp())
            query = query.where(CallLog.ts < end_time.timestamp())
        result = await db.execute(query)
        rows = result.scalars().all()

        # Calc main values
        total_calls = len(rows)
        success_count = calc_success_logs(rows)
        success_rate = success_count / (total_calls or 1) * 100
        total_minutes = calc_total_minutes(rows)
        total_cost = calc_total_cost(rows)

        # Calc dispositions
        dispositions = {
            "qualified": len([row for row in rows if is_qualified(row)]),
            "answering": len([row for row in rows if is_answering(row)]),
            "no_answer": len([row for row in rows if is_no_answer(row)]),
            "busy": len([row for row in rows if is_busy(row)]),
        }

        # Calc performances by agent
        performances = []
        grouped = group_by_agent(rows)
        for key, agent_rows in grouped.items():
            agent = next((agent for agent in agents if agent.get("id") == key), None)
            if agent:
                agent_total_minutes = calc_total_minutes(agent_rows)
                agent_total_cost = calc_total_cost(agent_rows)
                cost_per_minute = agent_total_cost / (agent_total_minutes or 1)
                performances.append({
                    "agent_name": agent.get("name", "(Unnamed)"),
                    "total_call": len(agent_rows),
                    "total_minutes": round(agent_total_minutes, 2),
                    "total_cost": round(agent_total_cost, 2),
                    "cost_per_minute": round(cost_per_minute, 3),
                    "success_call": calc_success_logs(agent_rows),
                })

        return {
            "total_calls": total_calls,
            "total_minutes": round(total_minutes, 2),
            "total_cost": round(total_cost, 2),
            "success_rate": round(success_rate, 2),
            "dispositions": dispositions,
            "performances": performances,
        }
    except HTTPException:
        raise
    except Exception as e:
        print("----------------------")
        print(e)
        print("----------------------")
        raise HTTPException(status_code=500, detail=str(e))
