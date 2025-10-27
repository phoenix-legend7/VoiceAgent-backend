from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List
import httpx
import uuid
from pydantic import BaseModel

from app.routers.auth import current_active_user
from app.utils.httpx import get_httpx_headers, httpx_base_url
from app.core.database import get_db
from app.models import User
from app.schemas.auth import UserRead, UserUpdate
from app.utils.auth import get_user_manager

router = APIRouter()

class UserStatusUpdate(BaseModel):
    is_active: bool

def require_admin(current_user: User = Depends(current_active_user)):
    """Dependency to require admin/superuser privileges"""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return current_user

async def get_user_info():
    try:
        async with httpx.AsyncClient() as client:
            headers = get_httpx_headers()
            response = await client.get(f"{httpx_base_url}/user/info", headers=headers)
            if response.status_code != 200 and response.status_code != 201:
                raise HTTPException(status_code=response.status_code, detail=response.text or "Unknown Error")
            return response.json()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/all", response_model=List[UserRead])
async def get_all_users(
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin)
):
    """
    Get all users. Requires admin privileges.
    """
    try:
        # Query all users from the database
        stmt = select(User)
        result = await db.execute(stmt)
        users = result.scalars().unique().all()  # Use unique() to avoid joined eager load issues

        # Convert to UserRead schema
        return [UserRead.model_validate(user) for user in users]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats")
async def get_users_stats(
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin)
):
    """
    Get numbers of total users and active users. Requries admin privileges.
    """
    try:
        # Count total users
        total_stmt = select(func.count(User.id))
        total_result = await db.execute(total_stmt)
        total_users = total_result.scalar() or 0

        # Count active users
        active_stmt = select(func.count(User.id)).where(User.is_active == True)
        active_result = await db.execute(active_stmt)
        active_users = active_result.scalar() or 0

        return {
            "total_users": total_users,
            "active_users": active_users
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/{user_id}/status")
async def update_user_status(
    user_id: str,
    status_update: UserStatusUpdate,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin),
    user_manager = Depends(get_user_manager)
):
    """
    Update user status (is_active). Requires admin privileges.
    """
    try:
        # Convert string to UUID
        try:
            user_uuid = uuid.UUID(user_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid user ID format")
        
        # Get the user to update
        user = await user_manager.get(user_uuid)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Create UserUpdate with only is_active field
        user_update = UserUpdate(is_active=status_update.is_active)
        
        # Update the user
        updated_user = await user_manager.update(
            user_update=user_update,
            user=user,
            safe=False  # Allow updating any field including is_active
        )
        
        return UserRead.model_validate(updated_user)
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
