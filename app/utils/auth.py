from fastapi import Depends
from fastapi_users import BaseUserManager, UUIDIDMixin
from fastapi_users.db import SQLAlchemyUserDatabase
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import Optional
import uuid
from app.core.config import settings
from app.models import User, OAuthAccount
from app.core.database import SessionLocal

class UserDatabase(SQLAlchemyUserDatabase[User, OAuthAccount]):
    async def get_by_oauth_account(self, oauth: str, account_id: str) -> Optional[User]:
        stmt = (
            select(User)
            .join(OAuthAccount)
            .where(
                OAuthAccount.oauth_name == oauth,
                OAuthAccount.account_id == account_id,
            )
            .options(selectinload(User.oauth_accounts))  # load accounts non-joined
        )
        result = await self.session.execute(stmt)
        return result.unique().scalar_one_or_none()

class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    reset_password_token_secret = settings.JWT_SECRET_KEY
    verification_token_secret = settings.JWT_SECRET_KEY

    async def on_after_register(self, user: User, request=None):
        print(f"User {user.id} has registered.")

async def get_user_db():
    async with SessionLocal() as session:
        yield UserDatabase(session, User, OAuthAccount)

async def get_user_manager(user_db=Depends(get_user_db)):
    yield UserManager(user_db)
