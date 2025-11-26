from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import time

from app.core.database import get_db
from app.models import AutomationWebhook
from app.routers.auth import current_active_user
from app.models import User

router = APIRouter()

class WebhookRequest(BaseModel):
    webhook_url: str
    automation_id: str | None = None

@router.post("/webhook")
async def create_webhook(
    webhook_request: WebhookRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(current_active_user)
):
    """
    Create or update a webhook for automation.
    Saves webhook_url and optional automation_id per user.
    """
    try:
        if webhook_request.automation_id:
            stmt = select(AutomationWebhook).where(
                AutomationWebhook.user_id == current_user.id,
                AutomationWebhook.automation_id == webhook_request.automation_id
            )
        else:
            stmt = select(AutomationWebhook).where(
                AutomationWebhook.user_id == current_user.id,
                AutomationWebhook.automation_id.is_(None)
            )
        
        result = await db.execute(stmt)
        existing_webhook = result.scalar_one_or_none()
        
        if existing_webhook:
            # Update existing webhook
            existing_webhook.webhook_url = webhook_request.webhook_url
            existing_webhook.automation_id = webhook_request.automation_id
            await db.commit()
            await db.refresh(existing_webhook)
            return {
                "id": str(existing_webhook.id),
                "webhook_url": existing_webhook.webhook_url,
                "automation_id": existing_webhook.automation_id,
                "created_at": existing_webhook.created_at,
                "message": "Webhook updated successfully"
            }
        else:
            # Create new webhook
            new_webhook = AutomationWebhook(
                webhook_url=webhook_request.webhook_url,
                automation_id=webhook_request.automation_id,
                user_id=current_user.id,
                created_at=int(time.time() * 1000)  # milliseconds timestamp
            )
            db.add(new_webhook)
            await db.commit()
            await db.refresh(new_webhook)
            return {
                "id": str(new_webhook.id),
                "webhook_url": new_webhook.webhook_url,
                "automation_id": new_webhook.automation_id,
                "created_at": new_webhook.created_at,
                "message": "Webhook created successfully"
            }
    
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

