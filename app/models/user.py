from fastapi_users.db import SQLAlchemyBaseUserTableUUID
from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List, Optional
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

    oauth_accounts: Mapped[List[OAuthAccount]] = relationship(
        "OAuthAccount", cascade="all, delete-orphan", lazy="joined"
    )
