from sqlalchemy import Column, Text, JSON, BigInteger, String
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base

class Agent(Base):
    __tablename__ = "agents"

    id = Column(String, primary_key=True,unique=True, nullable=False)
    name = Column(Text)
    config = Column(JSON, nullable=True)
    created_at = Column(BigInteger, nullable=True)
    user_id = Column(UUID(as_uuid=True), nullable=True)
