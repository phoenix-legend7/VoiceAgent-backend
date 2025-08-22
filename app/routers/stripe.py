from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer
from pydantic import BaseModel
from sqlalchemy import select
from dotenv import load_dotenv
import os
import stripe
import logging

from app.core.database import get_db_background
from app.models import User
from app.routers.auth import current_active_user

# Load environment variables
load_dotenv()

# Initialize Stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

router = APIRouter()
security = HTTPBearer()

# Pydantic models
class PaymentMethodRequest(BaseModel):
    payment_method_id: str

class AutoRefillSettings(BaseModel):
    threshold: float
    refill_amount: float
    enabled: bool

class WebhookData(BaseModel):
    type: str
    data: dict

class ManualTopupRequest(BaseModel):
    amount: float

def cents_to_dollars(cents: int) -> float:
    return cents / 100

def dollars_to_cents(dollars: float) -> int:
    return int(dollars * 100)

# Stripe API endpoints
@router.post("/setup-payment-method")
async def setup_payment_method(
    request: PaymentMethodRequest, 
    user: User = Depends(current_active_user)
):
    try:
        # Create or retrieve Stripe customer
        if not user.stripe_customer_id:
            customer = stripe.Customer.create(
                email=user.email,
                metadata={'user_id': user.id}
            )
            user.stripe_customer_id = customer.id
            # Save to database
            await save_user(user)
        
        # Attach payment method to customer
        payment_method = stripe.PaymentMethod.attach(
            request.payment_method_id,
            customer=user.stripe_customer_id,
        )
        
        # Set as default payment method
        stripe.Customer.modify(
            user.stripe_customer_id,
            invoice_settings={'default_payment_method': payment_method.id}
        )
        
        user.default_payment_method = payment_method.id
        await save_user(user)
        
        return {
            "success": True,
            "payment_method": {
                "id": payment_method.id,
                "type": payment_method.type,
                "card": {
                    "brand": payment_method.card.brand,
                    "last4": payment_method.card.last4,
                    "exp_month": payment_method.card.exp_month,
                    "exp_year": payment_method.card.exp_year,
                } if payment_method.type == "card" else None
            }
        }
    
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/payment-methods")
async def get_payment_methods(user: User = Depends(current_active_user)):
    try:
        if not user.stripe_customer_id:
            return {"payment_methods": []}
        
        payment_methods = stripe.PaymentMethod.list(
            customer=user.stripe_customer_id,
            type="card",
        )
        
        formatted_methods = []
        for pm in payment_methods.data:
            formatted_methods.append({
                "id": pm.id,
                "type": pm.type,
                "card": {
                    "brand": pm.card.brand,
                    "last4": pm.card.last4,
                    "exp_month": pm.card.exp_month,
                    "exp_year": pm.card.exp_year,
                },
                "is_default": pm.id == user.default_payment_method
            })
        
        return {"payment_methods": formatted_methods}
    
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/auto-refill/configure")
async def configure_auto_refill(
    settings: AutoRefillSettings,
    user: User = Depends(current_active_user)
):
    if not user.default_payment_method:
        raise HTTPException(
            status_code=400, 
            detail="Please add a payment method before enabling auto-refill"
        )
    
    user.auto_refill = settings.enabled
    user.auto_threshold = dollars_to_cents(settings.threshold)
    user.auto_refill_amount = dollars_to_cents(settings.refill_amount)
    
    await save_user(user)
    
    return {
        "success": True,
        "auto_refill_enabled": user.auto_refill,
        "threshold": cents_to_dollars(user.auto_threshold),
        "refill_amount": cents_to_dollars(user.auto_refill_amount)
    }

@router.post("/manual-topup")
async def manual_topup(
    request: ManualTopupRequest,
    user: User = Depends(current_active_user)
):
    try:
        if not user.default_payment_method:
            raise HTTPException(
                status_code=400,
                detail="No payment method available"
            )

        amount = request.amount

        # Create payment intent
        payment_intent = stripe.PaymentIntent.create(
            amount=dollars_to_cents(amount),
            currency='usd',
            customer=user.stripe_customer_id,
            payment_method=user.default_payment_method,
            confirm=True,
            return_url="https://yoursite.com/billing",
            metadata={
                'user_id': user.id,
                'type': 'manual_topup'
            }
        )
        
        if payment_intent.status == 'succeeded':
            user.total_credit += dollars_to_cents(amount)
            await save_user(user)
            
            return {
                "success": True,
                "amount_added": amount,
                "new_balance": cents_to_dollars(user.total_credit - user.used_credit)
            }
        
        return {"success": False, "status": payment_intent.status}
    
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/payment-methods/{payment_method_id}")
async def delete_payment_method(
    payment_method_id: str,
    user: User = Depends(current_active_user)
):
    """Delete a payment method for the current user"""
    try:
        if not user.stripe_customer_id:
            raise HTTPException(
                status_code=404,
                detail="No Stripe customer found"
            )
        
        # Verify the payment method belongs to this user
        payment_methods = stripe.PaymentMethod.list(
            customer=user.stripe_customer_id,
            type="card",
        )
        
        payment_method_exists = any(pm.id == payment_method_id for pm in payment_methods.data)
        if not payment_method_exists:
            raise HTTPException(
                status_code=404,
                detail="Payment method not found or doesn't belong to this user"
            )
        
        # Check if this is the default payment method
        if user.default_payment_method == payment_method_id:
            # Remove default payment method from user
            user.default_payment_method = None
            await save_user(user)
            
            # Remove default payment method from Stripe customer
            stripe.Customer.modify(
                user.stripe_customer_id,
                invoice_settings={'default_payment_method': None}
            )
        
        # Detach the payment method from the customer
        stripe.PaymentMethod.detach(payment_method_id)
        
        return {
            "success": True,
            "message": "Payment method deleted successfully"
        }
    
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/check-auto-refill")
async def check_and_process_auto_refill(user: User = Depends(current_active_user)):
    """Check if user needs auto-refill and process it"""
    if not user.auto_refill or not user.default_payment_method:
        return {"refill_needed": False}

    available_credit = user.total_credit - user.used_credit
    
    if available_credit <= user.auto_threshold:
        try:
            payment_intent = stripe.PaymentIntent.create(
                amount=user.auto_refill_amount,
                currency='usd',
                customer=user.stripe_customer_id,
                payment_method=user.default_payment_method,
                confirm=True,
                return_url="https://yoursite.com/billing",
                metadata={
                    'user_id': user.id,
                    'type': 'auto_refill'
                }
            )
            
            if payment_intent.status == 'succeeded':
                user.total_credit += user.auto_refill_amount
                await save_user(user)
                
                # Log the auto-refill
                await log_auto_refill(user.id, cents_to_dollars(user.auto_refill_amount))
                
                return {
                    "refill_processed": True,
                    "amount": cents_to_dollars(user.auto_refill_amount),
                    "new_balance": cents_to_dollars(user.total_credit - user.used_credit)
                }
            
            return {"refill_processed": False, "status": payment_intent.status}
        
        except stripe.error.StripeError as e:
            logging.error(f"Auto-refill failed for user {user.id}: {str(e)}")
            return {"refill_processed": False, "error": str(e)}
    
    return {"refill_needed": False}

# Background task to check all users for auto-refill
async def process_all_auto_refills():
    """Background task to process auto-refills for all users"""
    # This should be called by a cron job or background task scheduler
    users_needing_refill = await get_users_needing_auto_refill()
    
    results = []
    for user in users_needing_refill:
        result = await check_and_process_auto_refill(user)
        results.append({"user_id": user.id, "result": result})
    
    return {"processed": len(results), "results": results}

# Utility functions (implement according to your database)
async def save_user(user: User):
    """Save user to database"""
    try:
        async with get_db_background() as session:
            # Use merge to attach possibly detached instances coming from request context
            merged_user = await session.merge(user)
            try:
                await session.commit()
            except Exception as e:
                await session.rollback()
                logging.error(f"Failed to save user {getattr(user, 'id', None)}: {str(e)}")
                raise
            # Refresh to get any DB-side defaults/updates
            try:
                await session.refresh(merged_user)
            except Exception:
                # Safe to ignore refresh failures in background contexts
                pass
            return merged_user
    except Exception as e:
        # Bubble up so API handlers can translate to HTTP errors
        raise e

async def get_users_needing_auto_refill():
    """Get all users who need auto-refill"""
    try:
        async with get_db_background() as session:
            stmt = (
                select(User)
                .where(
                    User.auto_refill == True,  # noqa: E712
                    User.default_payment_method.is_not(None),
                    (User.total_credit - User.used_credit) <= User.auto_threshold,
                )
            )
            result = await session.execute(stmt)
            return result.scalars().all()
    except Exception as e:
        logging.error(f"Failed to fetch users needing auto-refill: {str(e)}")
        raise e

async def log_auto_refill(user_id: str, amount: float):
    """Log auto-refill transaction"""
    # No dedicated billing/transactions table exists; log to application logs for observability
    try:
        logging.info(f"Auto-refill processed for user {user_id}: ${amount:.2f}")
    except Exception:
        # Avoid raising from logging issues
        pass
