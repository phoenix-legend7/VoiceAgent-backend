from fastapi import APIRouter, Depends, HTTPException
from fastapi_users import FastAPIUsers
from fastapi_users.authentication import BearerTransport, JWTStrategy, AuthenticationBackend
from fastapi_users.jwt import generate_jwt
from httpx_oauth.clients.google import GoogleOAuth2
from pydantic import BaseModel, EmailStr
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
import uuid
import httpx
import random
import secrets

from app.core.config import settings
from app.core.database import get_db
from app.utils.auth import get_user_manager
from app.models import User, VerificationCode
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

current_active_user = fastapi_users.current_user(active=True, verified=True)

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
    fastapi_users.get_verify_router(user_schema=UserRead), tags=["auth"]
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

class VerifyCodeRequest(BaseModel):
    email: EmailStr
    code: str

class ResendVerificationRequest(BaseModel):
    email: EmailStr

@router.post("/verify-code")
async def verify_email_with_code(
    request: VerifyCodeRequest,
    db: AsyncSession = Depends(get_db),
    user_manager=Depends(get_user_manager)
):
    """Verify email using verification code."""
    try:
        # Find the verification code
        stmt = select(VerificationCode).where(
            VerificationCode.email == request.email,
            VerificationCode.code == request.code,
            VerificationCode.used == False,
            VerificationCode.expires_at > datetime.utcnow()
        )
        result = await db.execute(stmt)
        verification_code = result.scalar_one_or_none()
        
        if not verification_code:
            raise HTTPException(status_code=400, detail="Invalid or expired verification code.")
        
        # Get the user using the same db session to avoid session conflicts
        from app.models import User
        user_stmt = select(User).where(User.email == request.email)
        user_result = await db.execute(user_stmt)
        user = user_result.unique().scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found.")
        
        if user.is_verified:
            # Mark code as used anyway
            verification_code.used = True
            await db.commit()
            # Generate JWT token for auto-login even if already verified
            jwt_data = {"sub": str(user.id), "aud": ["fastapi-users:auth"]}
            token = generate_jwt(
                data=jwt_data,
                secret=settings.JWT_SECRET_KEY,
                lifetime_seconds=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
            )
            return {
                "message": "Email is already verified.",
                "access_token": token,
                "token_type": "bearer"
            }
        
        # Verify the user by setting is_verified = True
        user.is_verified = True
        
        # Mark code as used
        verification_code.used = True
        
        # Commit both changes in the same transaction
        await db.commit()
        
        # Call the on_after_verify hook
        await user_manager.on_after_verify(user)
        
        # Generate JWT token for auto-login
        jwt_data = {"sub": str(user.id), "aud": ["fastapi-users:auth"]}
        token = generate_jwt(
            data=jwt_data,
            secret=settings.JWT_SECRET_KEY,
            lifetime_seconds=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
        
        return {
            "message": "Email verified successfully.",
            "access_token": token,
            "token_type": "bearer"
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        import logging
        logging.error(f"Error verifying email: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to verify email: {str(e)}")

@router.post("/resend-verification")
async def resend_verification_email(
    request: ResendVerificationRequest,
    db: AsyncSession = Depends(get_db),
    user_manager=Depends(get_user_manager)
):
    """Resend verification email with code to user."""
    from app.utils.email import email_service
    from datetime import timedelta
    
    try:
        user = await user_manager.get_by_email(request.email)
        if not user:
            # Don't reveal if user exists or not for security
            return {"message": "If an account exists with this email, a verification email has been sent."}
        
        if user.is_verified:
            return {"message": "Email is already verified."}
        
        # Delete old unused codes for this user
        delete_stmt = delete(VerificationCode).where(
            VerificationCode.user_id == user.id,
            VerificationCode.used == False
        )
        await db.execute(delete_stmt)
        await db.commit()
        
        # Generate new 6-digit verification code
        verification_code = f"{random.randint(100000, 999999)}"
        
        # Store verification code in database
        expires_at = datetime.utcnow() + timedelta(hours=24)
        db_code = VerificationCode(
            user_id=user.id,
            email=user.email,
            code=verification_code,
            expires_at=expires_at,
            used=False
        )
        db.add(db_code)
        await db.commit()
        
        # Send verification email with code
        await email_service.send_verification_email(
            to_email=user.email,
            verification_code=verification_code
        )
        
        return {"message": "If an account exists with this email, a verification email has been sent."}
    except Exception as e:
        # Don't reveal errors for security
        return {"message": "If an account exists with this email, a verification email has been sent."}

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

@router.post("/forgot-password")
async def forgot_password(
    request: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
    user_manager=Depends(get_user_manager)
):
    """Request a password reset email."""
    from app.utils.email import email_service
    from app.models import User
    
    try:
        # Find user by email
        user_stmt = select(User).where(User.email == request.email)
        result = await db.execute(user_stmt)
        user = result.unique().scalar_one_or_none()
        
        # Always return success message for security (don't reveal if user exists)
        if not user:
            return {"message": "If an account exists with this email, a password reset link has been sent."}

        # Only allow password reset for email/password accounts (not OAuth-only)
        if (not user.hashed_password) or (user.oauth_accounts and len(user.oauth_accounts) > 0):
            return {"message": "If an account exists with this email, a password reset link has been sent."}
        
        # Generate secure random token
        reset_token = secrets.token_urlsafe(32)
        
        # Set token and expiry (1 hour from now)
        user.reset_password_token = reset_token
        user.reset_password_token_expires = datetime.utcnow() + timedelta(hours=1)
        
        await db.commit()
        
        # Send password reset email
        await email_service.send_password_reset_email(
            to_email=user.email,
            reset_token=reset_token
        )
        
        return {"message": "If an account exists with this email, a password reset link has been sent."}
    except Exception as e:
        import logging
        logging.error(f"Error in forgot password: {str(e)}")
        # Don't reveal errors for security
        return {"message": "If an account exists with this email, a password reset link has been sent."}

@router.post("/reset-password")
async def reset_password(
    request: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
    user_manager=Depends(get_user_manager)
):
    """Reset password using the token from email."""
    from app.models import User
    from fastapi_users.password import PasswordHelper
    
    try:
        # Find user with valid reset token
        user_stmt = select(User).where(
            User.reset_password_token == request.token,
            User.reset_password_token_expires > datetime.utcnow()
        )
        result = await db.execute(user_stmt)
        user = result.unique().scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=400, detail="Invalid or expired reset token.")

        # Block reset for OAuth-only accounts even if a token exists
        if (not user.hashed_password) or (user.oauth_accounts and len(user.oauth_accounts) > 0):
            raise HTTPException(status_code=400, detail="Password reset is only available for email sign-up accounts.")
        
        # Hash the new password
        password_helper = PasswordHelper()
        hashed_password = password_helper.hash(request.new_password)
        
        # Update user password and clear reset token
        user.hashed_password = hashed_password
        user.reset_password_token = None
        user.reset_password_token_expires = None
        
        await db.commit()
        
        return {"message": "Password reset successfully."}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        import logging
        logging.error(f"Error resetting password: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to reset password: {str(e)}")
