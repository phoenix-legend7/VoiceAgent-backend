from fastapi import Depends, Request
from fastapi_users import BaseUserManager, UUIDIDMixin
from fastapi_users.db import SQLAlchemyUserDatabase
from fastapi_users import exceptions
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import Optional
from datetime import datetime, timedelta
import uuid
import random
import os
import logging
import stripe
from app.core.config import settings
from app.models import User, OAuthAccount, VerificationCode
from app.core.database import get_db
from app.utils.email import email_service

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

    async def authenticate(self, credentials):
        """Override authenticate to check if user is active."""
        try:
            user = await self.get_by_email(credentials.username)
        except exceptions.UserNotExists:
            # Run the hasher to mitigate timing attack
            self.password_helper.hash(credentials.password)
            return None

        verified, updated_password_hash = self.password_helper.verify_and_update(
            credentials.password, user.hashed_password
        )
        if not verified:
            return None
        
        # Check if user is active
        if not user.is_active:
            raise exceptions.UserInactive()

        # Update password hash to a more robust one if needed
        if updated_password_hash is not None:
            await self.user_db.update(user, {"hashed_password": updated_password_hash})

        return user

    async def on_after_register(self, user: User, request: Optional[Request] = None):
        """Send verification email with code after user registration."""
        print(f"User {user.id} has registered.")
        
        # Generate 6-digit verification code
        verification_code = f"{random.randint(100000, 999999)}"
        
        # Store verification code in database using the user_db session
        expires_at = datetime.utcnow() + timedelta(hours=24)
        db_code = VerificationCode(
            user_id=user.id,
            email=user.email,
            code=verification_code,
            expires_at=expires_at,
            used=False
        )
        self.user_db.session.add(db_code)
        await self.user_db.session.commit()
        
        # Send verification email with code
        try:
            email_sent = await email_service.send_verification_email(
                to_email=user.email,
                verification_code=verification_code
            )
            if email_sent:
                logging.info(f"Verification email sent successfully to {user.email}")
            else:
                logging.error(f"Failed to send verification email to {user.email}")
        except Exception as e:
            logging.error(f"Exception sending verification email to {user.email}: {str(e)}")

        # Create Stripe customer and start 30-day trial subscription automatically on signup
        try:
            stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
            if not stripe.api_key:
                logging.warning("STRIPE_SECRET_KEY not set; skipping trial subscription creation")
                return

            # Ensure Stripe customer exists
            if not getattr(user, "stripe_customer_id", None):
                customer = stripe.Customer.create(
                    email=user.email,
                    metadata={"user_id": str(user.id)}
                )
                user = await self.user_db.update(user, {"stripe_customer_id": customer.id})

            # Create subscription with 30-day trial for the single plan (1 agent by default)
            price_id = os.getenv("STRIPE_SINGLE_PLAN_PRICE_ID", "price_1SUfE3H5cS5BXfZcy9EEE8Rq")

            subscription = stripe.Subscription.create(
                customer=user.stripe_customer_id,
                items=[{"price": price_id, "quantity": 1}],
                trial_period_days=30,
                payment_settings={"save_default_payment_method": "on_subscription"},
                metadata={"user_id": str(user.id), "agent_quantity": "1"}
            )

            # Persist subscription details on the user
            # During trial, use trial_start/trial_end; otherwise use current_period_start/end
            start_date = None
            end_date = None

            if subscription.trial_end:
                # Subscription is in trial
                start_date = datetime.fromtimestamp(subscription.trial_start) if subscription.trial_start else None
                end_date = datetime.fromtimestamp(subscription.trial_end)
            elif subscription.current_period_start:
                # Subscription is active (no trial or trial ended)
                start_date = datetime.fromtimestamp(subscription.current_period_start)
                end_date = datetime.fromtimestamp(subscription.current_period_end)

            updates = {
                "stripe_subscription_id": subscription.id,
                "subscription_status": subscription.status,
                "subscription_plan": price_id,
                "subscription_quantity": 1,
                "subscription_start_date": start_date,
                "subscription_end_date": end_date,
            }
            await self.user_db.update(user, updates)
            logging.info(f"Created trial subscription for user {user.id}: {subscription.id}")

        except Exception as e:
            # Do not block registration on Stripe issues; just log
            logging.error(f"Failed to create trial subscription for user {user.id}: {e}")
    
    async def on_after_verify(self, user: User, request: Optional[Request] = None):
        """Called after user email is verified."""
        print(f"User {user.id} has verified their email.")

async def get_user_db(session = Depends(get_db)):
    # Use custom UserDatabase (with optimized get_by_oauth_account)
    yield UserDatabase(session, User, OAuthAccount)

async def get_user_manager(user_db=Depends(get_user_db)):
    yield UserManager(user_db)
