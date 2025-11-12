from sqlalchemy import Column, Text, JSON, BigInteger, String, Boolean
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base

class Agent(Base):
    __tablename__ = "agents"

    id = Column(String, primary_key=True,unique=True, nullable=False)
    name = Column(Text)
    config = Column(JSON, nullable=True)
    sip = Column(JSON, nullable=False, default={})
    tools = Column(JSON, nullable=False, default=[])
    created_at = Column(BigInteger, nullable=True)
    user_id = Column(UUID(as_uuid=True), nullable=True)
    stopped_due_to_credit = Column(Boolean, nullable=False, default=False)
