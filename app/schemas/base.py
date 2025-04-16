from pydantic import BaseModel

class ResponseBase(BaseModel):
    """Base response schema."""
    success: bool
    message: str = None 