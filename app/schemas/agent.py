from pydantic import BaseModel

class AgentBase(BaseModel):
    name: str
    config: dict

class AgentCreate(AgentBase):
    pass

class AgentUpdate(AgentBase):
    pass

class AgentDelete(AgentBase):
    pass

class AgentGet(AgentBase):
    id: str
    created_at: int
    pass
