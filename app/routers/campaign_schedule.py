from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from enum import Enum
from typing import Optional
from datetime import datetime

from app.core.database import get_db
from app.models import CampaignSchedule, FrequencyType
from app.routers.auth import current_active_user
from app.routers.campaigns import create_campaign, get_campaigns_db, set_caller, CreateCampaignRequest, SetCallerRequest
from app.services.campaign_scheduler import campaign_scheduler

class FrequencyEnum(str, Enum):
    DAILY = FrequencyType.DAILY.value
    CUSTOM = FrequencyType.CUSTOM.value
    WEEKDAYS = FrequencyType.WEEKDAYS.value
    WEEKENDS = FrequencyType.WEEKENDS.value
    WEEKLY = FrequencyType.WEEKLY.value
    MONTHLY = FrequencyType.MONTHLY.value

class CreateCampaignScheduleRequest(BaseModel):
    campaign_name: str
    caller: str
    frequency: FrequencyEnum
    start_time: int = None
    end_time: int = None

class CreateOnlyScheduleRequest(BaseModel):
    campaign_id: str
    campaign_name: str
    campaign_status: str
    caller: str
    frequency: FrequencyEnum
    start_time: int = None
    end_time: int = None
    created_at: int

class UpdateCampaignScheduleRequest(BaseModel):
    caller: Optional[str] = None
    start_time: Optional[int] = None
    end_time: Optional[int] = None
    frequency: Optional[FrequencyEnum] = None

router = APIRouter()

@router.get("/")
async def get_scheduled_campaigns(db: AsyncSession = Depends(get_db), user = Depends(current_active_user)):
    try:
        campaigns_millis = await get_campaigns_db(db, user)
        result = await db.execute(select(CampaignSchedule).where(CampaignSchedule.user_id == user.id))
        db_campaigns = result.scalars().all()
        scheduled_campaigns = []
        not_scheduled_campaigns = []
        for campaign_millis in campaigns_millis:
            db_campaign = next((camp for camp in db_campaigns if campaign_millis.get("id") == camp.id), None)
            if db_campaign:
                scheduled_campaigns.append({
                    "id": db_campaign.campaign_id,
                    "created_at": db_campaign.created_at,
                    "start_time": db_campaign.start_time,
                    "end_time": db_campaign.end_time,
                    "error": db_campaign.error,
                    "frequency": db_campaign.frequency,
                    "status": db_campaign.status,
                    "campaign_name": campaign_millis.get("name", None),
                    "campaign_status": campaign_millis.get("status", None),
                    "caller": campaign_millis.get("caller", None),
                })
            else:
                not_scheduled_campaigns.append(campaign_millis)
        return {
            "scheduled_campaigns": scheduled_campaigns,
            "not_scheduled_campaigns": not_scheduled_campaigns,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/")
async def create_campaign_schedule(
    request: CreateCampaignScheduleRequest,
    db: AsyncSession = Depends(get_db),
    user = Depends(current_active_user)
):
    try:
        # Create campaign in MillisAI
        campaign = await create_campaign(
            CreateCampaignRequest(name=request.campaign_name),
            db,
            user
        )
        campaign_id = campaign.get("id")
        if not campaign_id:
            raise HTTPException(status_code=400, detail="Failed to create campaign.")

        # Set caller to campaign
        await set_caller(
            campaign_id,
            SetCallerRequest(caller=request.caller),
            db,
            user
        )

        # Save campaign data to database
        campaign_schedule = CampaignSchedule(
            campaign_id = campaign.get("id"),
            campaign_name = campaign.get("name"),
            campaign_status = campaign.get("status"),
            caller = request.caller,
            start_time = request.start_time,
            end_time = request.end_time,
            frequency = FrequencyType(request.frequency.value),
            created_at = campaign.get("created_at"),
            user_id = user.id,
        )

        try:
            db.add(campaign_schedule)
            await db.commit()
            await db.refresh(campaign_schedule)

        except Exception as e:
            await db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to save to database: {str(e)}")

        # Schedule the campaign
        await campaign_scheduler.schedule_campaign(campaign_schedule)

        return campaign_schedule
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/exist")
async def create_only_campaign_schedule(
    request: CreateOnlyScheduleRequest,
    db: AsyncSession = Depends(get_db),
    user = Depends(current_active_user)
):
    try:
        campaign_id = request.campaign_id
        result = await db.execute(
            select(CampaignSchedule)
            .where(
                CampaignSchedule.campaign_id == campaign_id,
                CampaignSchedule.user_id == user.id
            )
        )
        db_campaign = result.scalar_one_or_none()
        if db_campaign:
            raise HTTPException(400, detail=f"Campaign {campaign_id} has already scheduled")

        # Set caller to campaign
        await set_caller(
            campaign_id,
            SetCallerRequest(caller=request.caller),
            db,
            user
        )

        # Save campaign data to database
        campaign_schedule = CampaignSchedule(
            campaign_id = campaign_id,
            campaign_name = request.campaign_name,
            campaign_status = request.campaign_status,
            caller = request.caller,
            start_time = request.start_time,
            end_time = request.end_time,
            frequency = FrequencyType(request.frequency.value),
            created_at = request.created_at,
            user_id = user.id,
        )

        try:
            db.add(campaign_schedule)
            await db.commit()
            await db.refresh(campaign_schedule)

        except Exception as e:
            await db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to save to database: {str(e)}")

        # Schedule the campaign
        await campaign_scheduler.schedule_campaign(campaign_schedule)

        return campaign_schedule
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{campaign_id}/pause")
async def pause_campaign_schedule(
    campaign_id: str,
    status: str = "paused",
    db: AsyncSession = Depends(get_db),
    user = Depends(current_active_user)
):
    try:
        if not status in ["paused", "scheduled"]:
            raise HTTPException(status_code=402, detail="Status is invalid")

        result = await db.execute(
            select(CampaignSchedule)
            .where(
                CampaignSchedule.campaign_id == campaign_id,
                CampaignSchedule.user_id == user.id
            )
        )
        campaign_schedule = result.scalar_one_or_none()
        if not campaign_schedule:
            raise HTTPException(status_code=404, detail="Campaign schedule not found")

        if status == "paused" and campaign_schedule.status == "paused":
            raise HTTPException(status_code=400, detail="Campaign schedule is already paused")

        if status == "scheduled" and campaign_schedule.status == "scheduled":
            raise HTTPException(status_code=400, detail="Campaign schedule is already not started")

        if campaign_schedule.status == "active":
            # Stop the campaign if it's running
            # await stop_campaign(campaign_schedule.campaign_id)
            print(f"Campaign {campaign_schedule.campaign_id} stopped")

        # Remove from scheduler
        await campaign_scheduler.remove_campaign(campaign_schedule.id)

        # Update status to paused
        campaign_schedule.status = status
        try:
            await db.commit()
            await db.refresh(campaign_schedule)
        except Exception as e:
            await db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to save to database: {str(e)}")

        return campaign_schedule
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{campaign_id}/resume")
async def resume_campaign_schedule(
    campaign_id: str,
    db: AsyncSession = Depends(get_db),
    user = Depends(current_active_user)
):
    try:
        result = await db.execute(
            select(CampaignSchedule)
            .where(
                CampaignSchedule.campaign_id == campaign_id,
                CampaignSchedule.user_id == user.id
            )
        )
        campaign_schedule = result.scalar_one_or_none()
        if not campaign_schedule:
            raise HTTPException(status_code=404, detail="Campaign schedule not found")

        if campaign_schedule.status != "paused":
            raise HTTPException(status_code=400, detail="Campaign schedule is not paused")

        # Reschedule the campaign
        await campaign_scheduler.schedule_campaign(campaign_schedule)

        # Update status to scheduled
        campaign_schedule.status = "scheduled"
        try:
            await db.commit()
            await db.refresh(campaign_schedule)
        except Exception as e:
            await db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to save to database: {str(e)}")

        return campaign_schedule
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{campaign_id}")
async def update_campaign_schedule(
    campaign_id: str,
    request: UpdateCampaignScheduleRequest,
    db: AsyncSession = Depends(get_db),
    user = Depends(current_active_user)
):
    try:
        result = await db.execute(
            select(CampaignSchedule)
            .where(
                CampaignSchedule.campaign_id == campaign_id,
                CampaignSchedule.user_id == user.id
            )
        )
        campaign_schedule = result.scalar_one_or_none()
        if not campaign_schedule:
            raise HTTPException(status_code=404, detail="Campaign schedule not found")

        if campaign_schedule.status in ["active", "paused"]:
            raise HTTPException(status_code=400, detail="Campaign schedule is running. Please stop it and try again.")

        if request.caller != None:
            await set_caller(
                campaign_schedule.id,
                SetCallerRequest(caller=request.caller),
                db,
                user
            )
        if request.frequency != None:
            campaign_schedule.frequency = FrequencyType(request.frequency.value)
        if request.start_time != None:
            campaign_schedule.start_time = datetime.fromtimestamp(request.start_time / 1000)
        if request.end_time != None:
            campaign_schedule.end_time = datetime.fromtimestamp(request.end_time / 1000)

        try:
            await db.commit()
            await db.refresh(campaign_schedule)
        except Exception as e:
            await db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to save to database: {str(e)}")

        # Reschedule the campaign
        await campaign_scheduler.schedule_campaign(campaign_schedule)

        return campaign_schedule
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{campaign_id}")
async def delete_campaign_schedule(
    campaign_id: str,
    db: AsyncSession = Depends(get_db),
    user = Depends(current_active_user)
):
    try:
        result = await db.execute(
            select(CampaignSchedule)
            .where(
                CampaignSchedule.campaign_id == campaign_id,
                CampaignSchedule.user_id == user.id
            )
        )
        campaign_schedule = result.scalar_one_or_none()
        if not campaign_schedule:
            raise HTTPException(status_code=404, detail="Campaign schedule not found")

        if campaign_schedule.status in ["active", "paused"]:
            raise HTTPException(status_code=400, detail="Campaign schedule is running. Please stop it and try again.")

        # Remove from scheduler
        await campaign_scheduler.remove_campaign(campaign_schedule.id)

        try:
            # Delete from database
            await db.delete(campaign_schedule)
            await db.commit()
        except Exception as e:
            await db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to save to database: {str(e)}")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
