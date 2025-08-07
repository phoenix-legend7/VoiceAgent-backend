from fastapi import APIRouter
from fastapi_users import FastAPIUsers
from fastapi_users.authentication import CookieTransport, JWTStrategy, AuthenticationBackend
from httpx_oauth.clients.google import GoogleOAuth2
import uuid

from app.core.config import settings
from app.utils.auth import get_user_manager
from app.models import User
from app.schemas.auth import UserCreate, UserRead, UserUpdate

cookie_transport = CookieTransport(cookie_name="auth", cookie_max_age=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60)

def get_jwt_strategy():
    return JWTStrategy(secret=settings.JWT_SECRET_KEY, lifetime_seconds=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60)

auth_backend = AuthenticationBackend(
    name="jwt",
    transport=cookie_transport,
    get_strategy=get_jwt_strategy,
)

fastapi_users = FastAPIUsers[User, uuid.UUID](
    get_user_manager,
    [auth_backend],
)

google_client = GoogleOAuth2(
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
)

router = APIRouter()

router.include_router(
    fastapi_users.get_auth_router(auth_backend), prefix="/jwt", tags=["auth"]
)
router.include_router(
    fastapi_users.get_register_router(user_schema=UserRead, user_create_schema=UserCreate), tags=["auth"]
)
router.include_router(
    fastapi_users.get_users_router(user_schema=UserRead, user_update_schema=UserUpdate), prefix="/users", tags=["users"]
)

router.include_router(
    fastapi_users.get_oauth_router(
        google_client,
        auth_backend,
        state_secret=settings.JWT_SECRET_KEY,
        associate_by_email=True,
        redirect_url=settings.GOOGLE_REDIRECT_CALLBACK,
    ),
    prefix="/google",
    tags=["auth"],
)
