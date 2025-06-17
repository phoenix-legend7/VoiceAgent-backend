from datetime import datetime, timezone, time
from sqlalchemy import select, and_
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger

from app.core.database import get_db_background
from app.models.campaign_schedule import CampaignSchedule, FrequencyType
from app.routers.campaigns import start_campaign, stop_campaign

class CampaignScheduler:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.active_jobs = {}  # Store active job IDs
        self.working_hours_start = time(9, 0)  # 9 AM
        self.working_hours_end = time(17, 0)   # 5 PM

    async def start(self):
        """Start the scheduler and load existing campaigns"""
        if not self.scheduler.running:
            self.scheduler.start()
            await self.load_existing_campaigns()

    async def load_existing_campaigns(self):
        """Load and schedule existing campaigns from the database"""
        async with get_db_background() as db:
            result = await db.execute(
                select(CampaignSchedule).where(
                    and_(
                        CampaignSchedule.status == "scheduled",
                        CampaignSchedule.start_time > datetime.now(timezone.utc)
                    )
                )
            )
            campaigns = result.scalars().all()
            
            for campaign in campaigns:
                await self.schedule_campaign(campaign)

    async def schedule_campaign(self, campaign: CampaignSchedule):
        """Schedule a campaign based on its frequency and timing"""
        job_id = f"campaign_{campaign.id}"
        
        # Remove existing job if it exists
        if job_id in self.active_jobs:
            self.scheduler.remove_job(job_id)
            del self.active_jobs[job_id]

        # Create start and stop jobs
        start_job = self.scheduler.add_job(
            self.start_campaign_job,
            trigger=self._get_trigger(campaign),
            args=[campaign.id],
            id=f"{job_id}_start",
            replace_existing=True
        )

        # Only create stop job for custom schedules
        if campaign.frequency == FrequencyType.CUSTOM:
            stop_job = self.scheduler.add_job(
                self.stop_campaign_job,
                trigger=DateTrigger(run_date=campaign.end_time),
                args=[campaign.id],
                id=f"{job_id}_stop",
                replace_existing=True
            )
            self.active_jobs[job_id] = {
                "start_job": start_job,
                "stop_job": stop_job
            }
        else:
            # For other frequencies, create a daily stop job at 5 PM
            stop_job = self.scheduler.add_job(
                self.stop_campaign_job,
                trigger=CronTrigger(hour=17, minute=0),  # 5 PM
                args=[campaign.id],
                id=f"{job_id}_stop",
                replace_existing=True
            )
            self.active_jobs[job_id] = {
                "start_job": start_job,
                "stop_job": stop_job
            }

    def _get_trigger(self, campaign: CampaignSchedule):
        """Get the appropriate trigger based on frequency"""
        if campaign.frequency == FrequencyType.CUSTOM:
            return DateTrigger(run_date=campaign.start_time)
        else:
            # For all other frequencies, use working hours
            if campaign.frequency == FrequencyType.DAILY:
                return CronTrigger(
                    hour=self.working_hours_start.hour,
                    minute=self.working_hours_start.minute,
                    day_of_week='mon-sun'
                )
            elif campaign.frequency == FrequencyType.WEEKDAYS:
                return CronTrigger(
                    day_of_week='mon-fri',
                    hour=self.working_hours_start.hour,
                    minute=self.working_hours_start.minute
                )
            elif campaign.frequency == FrequencyType.WEEKENDS:
                return CronTrigger(
                    day_of_week='sat-sun',
                    hour=self.working_hours_start.hour,
                    minute=self.working_hours_start.minute
                )
            elif campaign.frequency == FrequencyType.WEEKLY:
                return CronTrigger(
                    day_of_week='mon',  # Default to Monday, can be made configurable
                    hour=self.working_hours_start.hour,
                    minute=self.working_hours_start.minute
                )
            elif campaign.frequency == FrequencyType.MONTHLY:
                return CronTrigger(
                    day=1,  # Default to 1st of month, can be made configurable
                    hour=self.working_hours_start.hour,
                    minute=self.working_hours_start.minute
                )

    async def start_campaign_job(self, campaign_id: str):
        """Job to start a campaign"""
        try:
            async with get_db_background() as db:
                result = await db.execute(
                    select(CampaignSchedule).where(CampaignSchedule.id == campaign_id)
                )
                campaign = result.scalar_one_or_none()
                
                if campaign and campaign.status == "scheduled":
                    # Check if current time is within working hours
                    current_time = datetime.now(timezone.utc).time()
                    if (self.working_hours_start <= current_time <= self.working_hours_end or 
                        campaign.frequency == FrequencyType.CUSTOM):
                        try:
                            # await start_campaign(campaign.campaign_id)
                            print(f"Campaign {campaign.campaign_id} started")
                            campaign.status = "active"
                            campaign.error = None
                        except Exception as e:
                            print(f"Failed to start campaign {campaign.campaign_id}")
                            campaign.status = "error"
                            campaign.error = str(e)
                        await db.commit()
        except Exception as e:
            print(f"Error starting campaign {campaign_id}: {str(e)}")

    async def stop_campaign_job(self, campaign_id: str):
        """Job to stop a campaign"""
        try:
            async with get_db_background() as db:
                result = await db.execute(
                    select(CampaignSchedule).where(CampaignSchedule.id == campaign_id)
                )
                campaign = result.scalar_one_or_none()

                if campaign and campaign.status == "active":
                    # await stop_campaign(campaign.campaign_id)
                    print(f"Campaign {campaign.campaign_id} stoped")
                    campaign.status = "scheduled"
                    await db.commit()
        except Exception as e:
            print(f"Error stopping campaign {campaign_id}: {str(e)}")

    async def remove_campaign(self, campaign_id: str):
        """Remove a campaign from the scheduler"""
        job_id = f"campaign_{campaign_id}"
        if job_id in self.active_jobs:
            jobs = self.active_jobs[job_id]
            self.scheduler.remove_job(jobs["start_job"].id)
            self.scheduler.remove_job(jobs["stop_job"].id)
            del self.active_jobs[job_id]

    def shutdown(self):
        """Shutdown the scheduler"""
        if self.scheduler.running:
            self.scheduler.shutdown()

# Create a global instance
campaign_scheduler = CampaignScheduler()
