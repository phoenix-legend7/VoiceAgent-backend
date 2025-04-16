from fastapi import APIRouter
from app.schemas.base import ResponseBase

router = APIRouter()

@router.get("/health", response_model=ResponseBase)
async def health_check():
    """Health check endpoint."""
    return ResponseBase(success=True, message="Service is healthy") 