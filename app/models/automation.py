from sqlalchemy import Column, Text, BigInteger, String
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.core.database import Base

class AutomationWebhook(Base):
    __tablename__ = "automation_webhooks"

    id = Column(UUID, primary_key=True, unique=True, nullable=False, default=uuid.uuid4)
    webhook_url = Column(Text, nullable=False)
    automation_id = Column(String, nullable=True)
    created_at = Column(BigInteger, nullable=True)
    user_id = Column(UUID(as_uuid=True), nullable=False)

