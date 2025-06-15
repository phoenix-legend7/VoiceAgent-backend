# Agent Schema
from pydantic import BaseModel
from typing import Optional, List

class CallLogBase(BaseModel):
    agent_id: Optional[str]
    agent_config: Optional[dict]
    duration: Optional[float]
    ts: Optional[float]
    chat: Optional[str]
    chars_used: Optional[float]
    session_id: Optional[str]
    call_id: Optional[str]
    cost_breakdown: Optional[List[dict]]
    voip: Optional[dict]
    recording: Optional[dict]
    metadata: Optional[dict]
    function_calls: Optional[List[dict]]
    call_status: Optional[str]
