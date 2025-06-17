from sqlalchemy import Column, DateTime, Text, BigInteger, Integer, Enum
from app.core.database import Base
import enum

class FrequencyType(enum.Enum):
    DAILY = "daily"
    CUSTOM = "custom"
    WEEKDAYS = "weekdays"
    WEEKENDS = "weekends"
    WEEKLY = "weekly"
    MONTHLY = "monthly"

class CampaignSchedule(Base):
    __tablename__ = "campaign_schedules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    campaign_id = Column(Text, nullable=False)
    campaign_name = Column(Text, nullable=False)
    campaign_status = Column(Text, nullable=False) # idle, started, paused, finished, failed
    caller = Column(Text, nullable=False)
    start_time = Column(DateTime(timezone=True), nullable=True)
    end_time = Column(DateTime(timezone=True), nullable=True)
    frequency = Column(Enum(FrequencyType), nullable=False, default=FrequencyType.DAILY)
    status = Column(Text, nullable=False, default="scheduled") # active, paused, scheduled, error
    error = Column(Text, nullable=True)
    created_at = Column(BigInteger, nullable=True)
