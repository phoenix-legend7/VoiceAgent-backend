# Agent Schema
from pydantic import BaseModel
from typing import Optional, List

class CampaignBase(BaseModel):
    name: str

class CampaignCreate(CampaignBase):
    pass

class CampaignRead(CampaignBase):
    id: str
    status: str
    records: List[dict] = []
    created_at: int
    include_metadata_in_prompt: Optional[bool] = False
    caller: str = None
