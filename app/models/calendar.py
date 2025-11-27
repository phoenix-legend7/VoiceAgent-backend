from sqlalchemy import Column, Text, BigInteger, String
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime, timezone
import uuid
from app.core.database import Base

class Calendar(Base):
    __tablename__ = "calendars"

    id = Column(UUID, primary_key=True, unique=True, nullable=False, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    name = Column(String, nullable=False)  # "get_available_meeting_slots" or "book_meeting_slot"
    title = Column(Text, nullable=False)  # User-friendly display name
    provider = Column(String, nullable=False, default="cal.com")
    api_key = Column(Text, nullable=False)  # Encrypted
    event_type_id = Column(String, nullable=False)
    contact_method = Column(String, nullable=True)  # "email" or "phone", only for "book_meeting_slot"
    created_at = Column(BigInteger, nullable=False, default=lambda: int(datetime.now(timezone.utc).timestamp()))
    updated_at = Column(BigInteger, nullable=False, default=lambda: int(datetime.now(timezone.utc).timestamp()), onupdate=lambda: int(datetime.now(timezone.utc).timestamp()))

