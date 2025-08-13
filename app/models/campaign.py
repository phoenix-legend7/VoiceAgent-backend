from sqlalchemy import Column, Text, JSON, BigInteger, String, Boolean
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base

class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(String, primary_key=True,unique=True, nullable=False)
    name = Column(Text)
    status = Column(Text, nullable=True, default="idle")
    caller = Column(Text, nullable=True)
    include_metadata_in_prompt = Column(Boolean, default=False)
    records = Column(JSON, nullable=False, default=[])
    created_at = Column(BigInteger, nullable=True)
    user_id = Column(UUID(as_uuid=True), nullable=True)
