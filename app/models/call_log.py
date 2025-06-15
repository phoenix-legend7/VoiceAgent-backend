from sqlalchemy import Column, Float, Text, JSON, Integer
from app.core.database import Base

class CallLog(Base):
    __tablename__ = "call_logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(Text, nullable=True)
    agent_config = Column(JSON, nullable=True) # Object
    duration = Column(Float, nullable=True)
    ts = Column(Float, nullable=True)
    chat = Column(Text, nullable=True)
    chars_used = Column(Float, nullable=True)
    session_id = Column(Text, nullable=True)
    call_id = Column(Text, nullable=True)
    cost_breakdown = Column(JSON, nullable=True) # Array
    voip = Column(JSON, nullable=True) # Object
    recording = Column(JSON, nullable=True) # Object
    call_metadata = Column(JSON, nullable=True) # Object
    function_calls = Column(JSON, nullable=True) # Array
    call_status = Column(Text, nullable=True)
