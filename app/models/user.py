from fastapi_users.db import SQLAlchemyBaseUserTableUUID
from sqlalchemy import Float, String, ForeignKey, Boolean, JSON, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List, Optional
from datetime import datetime
import uuid
from app.core.database import Base

class OAuthAccount(Base):
    __tablename__ = "oauth_account"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("user.id", ondelete="cascade"))
    oauth_name: Mapped[str] = mapped_column(String, index=True)
    access_token: Mapped[str] = mapped_column(String)
    expires_at: Mapped[Optional[int]] = mapped_column(nullable=True)
    refresh_token: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    account_id: Mapped[str] = mapped_column(String)
    account_email: Mapped[str] = mapped_column(String)

class User(SQLAlchemyBaseUserTableUUID, Base):
    __tablename__ = "user"

    first_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    avatar: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    total_credit: Mapped[Optional[float]] = mapped_column(Float, nullable=True, default=0)
    used_credit: Mapped[Optional[float]] = mapped_column(Float, nullable=True, default=0)
    auto_refill: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=False, default=False)
    auto_refill_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True, default=0)
    auto_threshold: Mapped[Optional[float]] = mapped_column(Float, nullable=True, default=0)
    stripe_customer_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    default_payment_method: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    # Subscription fields
    subscription_status: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # active, inactive, canceled, past_due
    subscription_plan: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # starter, professional, enterprise, etc.
    subscription_start_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    subscription_end_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    stripe_subscription_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    api_keys: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    reset_password_token: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    reset_password_token_expires: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    oauth_accounts: Mapped[List[OAuthAccount]] = relationship(
        "OAuthAccount", cascade="all, delete-orphan", lazy="joined"
    )
