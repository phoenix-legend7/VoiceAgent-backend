from sqlalchemy import Column, Text, BigInteger, Integer, Boolean, String
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from app.core.database import Base

class Tools(Base):
    __tablename__ = "tools"

    id = Column(UUID, primary_key=True, unique=True, nullable=False, default=uuid.uuid4)
    tool_id = Column(String, nullable=False)
    name = Column(Text, nullable=False)
    description = Column(Text, nullable=False)
    # Function/tool definition fields
    params = Column(JSONB, nullable=True)  # list of Param objects
    webhook = Column(Text, nullable=True)
    header = Column(JSONB, nullable=True)
    method = Column(Text, nullable=True)
    timeout = Column(Integer, nullable=True)
    run_after_call = Column(Boolean, nullable=True)
    messages = Column(JSONB, nullable=True)  # list of strings
    response_mode = Column(Text, nullable=True)  # "strict" | "flexible"
    execute_after_message = Column(Boolean, nullable=True)
    exclude_session_id = Column(Boolean, nullable=True)
    file_type = Column(Text, nullable=True)
    size = Column(BigInteger, nullable=True)
    created_at = Column(BigInteger, nullable=True)
    user_id = Column(UUID(as_uuid=True), nullable=True)
