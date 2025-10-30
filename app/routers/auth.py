from fastapi import APIRouter, Depends, HTTPException
from fastapi_users import FastAPIUsers
from fastapi_users.authentication import BearerTransport, JWTStrategy, AuthenticationBackend
from fastapi_users.jwt import generate_jwt
from httpx_oauth.clients.google import GoogleOAuth2
import uuid
import httpx

from app.core.config import settings
from app.utils.auth import get_user_manager
from app.models import User
from fastapi_users import exceptions as fau_exceptions
from app.schemas.auth import UserCreate, UserRead, UserUpdate

bearer_transport = BearerTransport(tokenUrl="auth/jwt/login")

def get_jwt_strategy():
    return JWTStrategy(secret=settings.JWT_SECRET_KEY, lifetime_seconds=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60)

auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)

fastapi_users = FastAPIUsers[User, uuid.UUID](
    get_user_manager,
    [auth_backend],
)

current_active_user = fastapi_users.current_user(active=True)

google_client = GoogleOAuth2(
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
    scopes=["openid", "email", "profile"]
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

@router.get("/google/verify")
async def google_callback(code: str, state: str, user_manager=Depends(get_user_manager)):
    token_data = await google_client.get_access_token(code, settings.GOOGLE_REDIRECT_CALLBACK)

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {token_data['access_token']}"},
            timeout=100
        )
        profile = resp.json()

    try:
        user = await user_manager.oauth_callback(
            oauth_name="google",
            access_token=token_data["access_token"],
            account_id=profile["id"],
            account_email=profile["email"]
        )
    except fau_exceptions.UserAlreadyExists:
        raise HTTPException(status_code=409, detail="User already exists for this email; account not linked.")
    await user_manager.update(
        user_update=UserUpdate(
            first_name=profile.get("given_name"),
            last_name=profile.get("family_name"),
            avatar=profile.get("picture"),
        ),
        user=user,
        safe=False  # allows updating any field
    )
    jwt_data = {"sub": str(user.id), "aud": ["fastapi-users:auth"]}
    token = generate_jwt(
        data=jwt_data,
        secret=settings.JWT_SECRET_KEY,
        lifetime_seconds=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )

    return {"access_token": token, "token_type": "bearer"}
