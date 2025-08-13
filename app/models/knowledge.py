from sqlalchemy import Column, Text, BigInteger, String
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base

class Knowledge(Base):
    __tablename__ = "knowledges"

    id = Column(String, primary_key=True, unique=True, nullable=False)
    name = Column(Text)
    description = Column(Text, nullable=True)
    file_type = Column(Text, nullable=True)
    size = Column(BigInteger, nullable=True)
    created_at = Column(BigInteger, nullable=True)
    user_id = Column(UUID(as_uuid=True), nullable=True)
