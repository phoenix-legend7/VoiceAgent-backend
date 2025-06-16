from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import select, func, text, case, Float, cast, literal_column, Numeric, lateral
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone, timedelta

from app.core.database import get_db
from app.models.call_log import CallLog

router = APIRouter()

# Helper function to extract cost from cost_breakdown array
def get_cost_expression():
    cost_subq = select(
        CallLog.id,
        cast(
            func.jsonb_array_elements(cast(CallLog.cost_breakdown, JSONB)).op('->>')('credit'),
            Float
        ).label('credit')
    ).where(
        func.jsonb_typeof(cast(CallLog.cost_breakdown, JSONB)) == 'array'
    ).subquery()
    
    return func.coalesce(func.sum(cost_subq.c.credit), 0.0)

# Helper to determine successful calls
def get_success_expression():
    # success_statuses = ['user-ended', 'agent-ended', 'api-ended', 'voicemail-message']
    # success_statuses = ['registered', 'queued', 'dispatching', 'provider_queued', 'initiated',
    #                     'ringing', 'in-progress', 'user-ended', 'agent-ended', 'api-ended',
    #                     'voicemail-hangup', 'voicemail-message', 'chat_completion']
    error_statuses = ['timeout', 'busy', 'no-answer', 'failed', 'canceled', 'error', 'unknown']
    return func.coalesce(
        func.sum(
            case(
                (CallLog.call_status.in_(error_statuses), 0),
                else_=1
            )
        )
    )

@router.get("/")
async def get_dashboard_data(
    agent_id: str = None,
    time_period: str = "today", # today, week, month, quarter
    db: AsyncSession = Depends(get_db)
):
    try:
        query = select(
            func.count().label("total_calls"),
            func.coalesce(func.sum(CallLog.duration) / 60, 0).label("total_minutes"),
            get_cost_expression().label("total_cost"),
            get_success_expression().label("success_count"),
            func.avg(CallLog.duration).label("avg_duration")
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
        row = result.first()
        success_rate = (row.success_count / row.total_calls * 100) if row.total_calls > 0 else 0
        return {
            "total_calls": row.total_calls,
            "total_minutes": round(row.total_minutes, 2) if row.total_minutes else 0,
            "total_cost": round(row.total_cost, 2) if row.total_cost else 0,
            "success_rate": round(success_rate, 2),
            "avg_call_duration": round(row.avg_duration, 2) if row.avg_duration else 0
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
