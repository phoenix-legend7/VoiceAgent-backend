from fastapi_users import schemas
from typing import Optional, Dict
import uuid
from datetime import datetime

class UserRead(schemas.BaseUser[uuid.UUID]):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    total_credit: Optional[float] = 0
    used_credit: Optional[float] = 0
    auto_refill: Optional[bool] = False
    auto_refill_amount: Optional[float] = 0
    auto_threshold: Optional[float] = 0
    avatar: Optional[str] = None
    api_keys: Optional[Dict[str, str]] = None
    # Subscription fields
    subscription_status: Optional[str] = None
    subscription_plan: Optional[str] = None
    subscription_start_date: Optional[datetime] = None
    subscription_end_date: Optional[datetime] = None
    stripe_subscription_id: Optional[str] = None

class UserCreate(schemas.BaseUserCreate):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    total_credit: Optional[float] = 0
    used_credit: Optional[float] = 0
    auto_refill: Optional[bool] = False
    auto_refill_amount: Optional[float] = 0
    auto_threshold: Optional[float] = 0
    avatar: Optional[str] = None

class UserUpdate(schemas.BaseUserUpdate):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    total_credit: Optional[float] = 0
    used_credit: Optional[float] = 0
    auto_refill: Optional[bool] = False
    auto_refill_amount: Optional[float] = 0
    auto_threshold: Optional[float] = 0
    avatar: Optional[str] = None
    is_active: Optional[bool] = None
    api_keys: Optional[Dict[str, str]] = None
    # Subscription fields
    subscription_status: Optional[str] = None
    subscription_plan: Optional[str] = None
    subscription_start_date: Optional[datetime] = None
    subscription_end_date: Optional[datetime] = None
    stripe_subscription_id: Optional[str] = None
