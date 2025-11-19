from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Dict
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

class ApiKeysUpdate(BaseModel):
    api_keys: Dict[str, str]

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

@router.get("/api-keys")
async def get_api_keys(
    current_user: User = Depends(current_active_user)
):
    """
    Get current user's API keys.
    """
    try:
        return {
            "api_keys": current_user.api_keys or {}
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/api-keys")
async def update_api_keys(
    api_keys_update: ApiKeysUpdate,
    current_user: User = Depends(current_active_user),
    user_manager = Depends(get_user_manager)
):
    """
    Update or save API keys for the current user.
    Merges new keys with existing keys (existing keys are preserved unless overwritten).
    """
    try:
        current_api_keys = current_user.api_keys or {}
        updated_api_keys = {**current_api_keys, **api_keys_update.api_keys}
        user_update = UserUpdate(api_keys=updated_api_keys)
        updated_user = await user_manager.update(
            user_update=user_update,
            user=current_user,
            safe=False
        )
        
        return {
            "api_keys": updated_user.api_keys or {},
            "message": "API keys updated successfully"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/api-keys/{key_name}")
async def delete_api_key(
    key_name: str,
    current_user: User = Depends(current_active_user),
    user_manager = Depends(get_user_manager)
):
    """
    Delete a specific API key by name.
    """
    try:
        current_api_keys = current_user.api_keys or {}

        if key_name not in current_api_keys:
            raise HTTPException(status_code=404, detail=f"API key '{key_name}' not found")

        updated_api_keys = {k: v for k, v in current_api_keys.items() if k != key_name}
        user_update = UserUpdate(api_keys=updated_api_keys)
        updated_user = await user_manager.update(
            user_update=user_update,
            user=current_user,
            safe=False
        )
        
        return {
            "api_keys": updated_user.api_keys or {},
            "message": f"API key '{key_name}' deleted successfully"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
