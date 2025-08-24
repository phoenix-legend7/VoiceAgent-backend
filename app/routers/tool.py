from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

from app.core.database import get_db
from app.models import Agent, Tools
from app.routers.auth import current_active_user

router = APIRouter()

TOOLS_REGISTRY: dict[str, dict[str, str]] = {
    # Communication
    "whatsapp-business": {"name": "WhatsApp Business", "description": "Send messages via WhatsApp Business API"},

    # CRM & Sales
    "pipedrive": {"name": "Pipedrive", "description": "Sync leads and deals with your sales pipeline"},
    "hubspot": {"name": "HubSpot CRM", "description": "Connect with your HubSpot contacts and deals"},
    "salesforce": {"name": "Salesforce", "description": "Integrate with Salesforce CRM data"},

    # Email & Communication
    "email": {"name": "Email Integration", "description": "Send follow-up emails automatically"},

    # Calendar & Scheduling
    "google-calendar": {"name": "Google Calendar", "description": "Schedule appointments automatically"},
    "calendly": {"name": "Calendly", "description": "Book meetings through Calendly integration"},
    "acuity-scheduling": {"name": "Acuity Scheduling", "description": "Schedule appointments with Acuity"},

    # Automation & Workflows
    "make": {"name": "Make.com", "description": "Create powerful automation workflows"},
    "zapier": {"name": "Zapier", "description": "Connect 6000+ apps with automation"},

    # E-commerce
    "shopify": {"name": "Shopify", "description": "Access your Shopify store data"},
    "woocommerce": {"name": "WooCommerce", "description": "Connect with your WooCommerce store"},

    # Analytics (commented in source list)
    # "google-analytics": {"name": "Google Analytics", "description": "Track website visitor data"},
}


class ToolParam(BaseModel):
    name: str
    required: bool
    type: str
    description: str


class ToolCreateRequest(BaseModel):
    tool_id: str
    name: str | None = None
    description: str | None = None
    params: list[ToolParam] | None = None
    webhook: str | None = None
    header: dict | None = None
    method: str | None = None


class ToolUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    params: list[ToolParam] | None = None
    webhook: str | None = None
    header: dict | None = None
    method: str | None = None


async def raise_for_tool(
    tool_id: str,
    db: AsyncSession,
    user
):
    # Check if the tool is connected to any agents
    result = await db.execute(select(Agent).where(Agent.user_id == user.id))
    agents = result.scalars().all()

    connected_agents = []
    for agent in agents:
        if agent.tools:
            # agent.tools is now a list of AgentToolRequest objects with 'id' field
            for tool in agent.tools:
                if tool.get('id') == tool_id:
                    connected_agents.append(agent.name)
                    break

    if connected_agents:
        agent_names = ", ".join(connected_agents)
        raise HTTPException(
            status_code=400, 
            detail=f"It is connected to the following agent(s): {agent_names}"
        )


@router.get("/")
async def list_tools(db: AsyncSession = Depends(get_db), user = Depends(current_active_user)):
    try:
        result = await db.execute(
            select(Tools.id, Tools.tool_id, Tools.name, Tools.description).where(Tools.user_id == user.id)
        )
        tools = result.all()
        return [
            {
                "id": tool.id,
                "tool_id": tool.tool_id,
                "name": tool.name,
                "description": tool.description
            }
            for tool in tools
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/custom")
async def list_custom_tools(db: AsyncSession = Depends(get_db), user = Depends(current_active_user)):
    try:
        result = await db.execute(select(Tools).where(Tools.tool_id == "custom", Tools.user_id == user.id))
        tools = result.scalars().all()
        return tools
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{tool_id}")
async def get_tool(tool_id: str, db: AsyncSession = Depends(get_db), user = Depends(current_active_user)):
    try:
        result = await db.execute(select(Tools).where(Tools.tool_id == tool_id, Tools.user_id == user.id))
        tool = result.scalar_one_or_none()
        if not tool:
            raise HTTPException(status_code=404, detail=f"Not found tool {tool_id}")
        return {
            "id": tool.id,
            "tool_id": tool.tool_id,
            "name": tool.name,
            "description": tool.description,
            "created_at": tool.created_at,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{id}")
async def update_tool(
    id: str,
    request: ToolUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user = Depends(current_active_user)
):
    result = await db.execute(select(Tools).where(Tools.id == id, Tools.tool_id == "custom", Tools.user_id == user.id))
    db_tool = result.scalar_one_or_none()
    if not db_tool:
        raise HTTPException(status_code=404, detail=f"Not found tool {id}")

    raise_for_tool(id, db, user)

    try:
        if request.name is not None:
            db_tool.name = request.name
        if request.description is not None:
            db_tool.description = request.description
        if request.params is not None:
            db_tool.params = [param.model_dump() for param in request.params]
        if request.webhook is not None:
            db_tool.webhook = request.webhook
        if request.header is not None:
            db_tool.header = request.header
        if request.method is not None:
            db_tool.method = request.method

        await db.commit()
        await db.refresh(db_tool)
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{id}")
async def delete_tool(id: str, db: AsyncSession = Depends(get_db), user = Depends(current_active_user)):
    result = await db.execute(select(Tools).where(Tools.id == id, Tools.user_id == user.id))
    db_tool = result.scalar_one_or_none()
    if not db_tool:
        raise HTTPException(status_code=404, detail=f"Not found tool {id}")

    raise_for_tool(id, db, user)

    try:
        await db.delete(db_tool)
        await db.commit()
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/")
async def create_tool(
    request: ToolCreateRequest,
    db: AsyncSession = Depends(get_db),
    user = Depends(current_active_user)
):
    try:
        tool_id = request.tool_id
        defaults = TOOLS_REGISTRY.get(tool_id)
        if tool_id != "custom" and not defaults:
            raise HTTPException(status_code=404, detail=f"Unknown tool_id {tool_id}")
        name = (
            request.name if tool_id == "custom" and request.name is not None else (defaults["name"] if defaults else "Custom tool")
        )
        description = (
            request.description if tool_id == "custom" and request.description is not None else (defaults["description"] if defaults else "User-defined tool")
        )
        result = await db.execute(select(Tools).where(Tools.tool_id == tool_id, Tools.user_id == user.id))
        db_tool = result.scalar_one_or_none()
        is_in_db = True
        if not db_tool:
            is_in_db = False
            db_tool = Tools(
                tool_id=tool_id,
                name=name,
                description=description,
                created_at=int(datetime.now(timezone.utc).timestamp()),
                user_id=user.id,
            )

        if tool_id == "email":
            # Email integration - requires SMTP configuration
            db_tool.method = "POST"
            smtp_server = request.header.get("smtp_server") if request.header else None
            smtp_port = request.header.get("smtp_port") if request.header else None
            email_username = request.header.get("email_username") if request.header else None
            email_password = request.header.get("email_password") if request.header else None

            if not all([smtp_server, smtp_port, email_username, email_password]):
                raise HTTPException(status_code=400, detail="SMTP configuration is required (smtp_server, smtp_port, email_username, email_password)")

            db_tool.header = {
                "smtp_server": smtp_server,
                "smtp_port": smtp_port,
                "email_username": email_username,
                "email_password": email_password,
            }
            db_tool.webhook = f"smtp://{smtp_server}:{smtp_port}"
            db_tool.params = [
                {"name": "to", "required": True, "type": "string", "description": "Recipient email address"},
                {"name": "subject", "required": True, "type": "string", "description": "Email subject"},
                {"name": "body", "required": True, "type": "string", "description": "Email body content"},
                {"name": "from_name", "required": False, "type": "string", "description": "Sender name"},
            ]

        elif tool_id == "whatsapp-business":
            db_tool.method = "POST"
            access_token = request.header.get("access_token") if request.header else None
            if not access_token:
                raise HTTPException(status_code=400, detail="Access token is required")
            phone_number_id = request.header.get("phone_number_id")
            if not phone_number_id:
                raise HTTPException(status_code=400, detail="Phone Number ID is required")
            db_tool.header = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}",
            }
            db_tool.webhook = f"https://graph.facebook.com/v20.0/{phone_number_id}/messages"
            db_tool.params = [
                {"name": "to", "required": True, "type": "string", "description": "Recipient phone number in international format"},
                {"name": "type", "required": True, "type": "string", "description": "Message type (text, template, etc.)"},
                {"name": "message", "required": False, "type": "string", "description": "Message payload depending on type"},
            ]

        elif tool_id == "woocommerce":
            db_tool.method = "GET"
            consumer_key = request.header.get("consumer_key") if request.header else None
            consumer_secret = request.header.get("consumer_secret") if request.header else None
            store_url = request.header.get("store_url") if request.header else None

            if not all([consumer_key, consumer_secret, store_url]):
                raise HTTPException(status_code=400, detail="WooCommerce configuration is required (consumer_key, consumer_secret, store_url)")

            db_tool.header = {
                "Consumer-Key": consumer_key,
                "Consumer-Secret": consumer_secret,
            }
            db_tool.webhook = f"{store_url.rstrip('/')}/wp-json/wc/v3"
            db_tool.params = [
                {"name": "endpoint", "required": True, "type": "string", "description": "API endpoint (e.g., products, orders, customers)"},
                {"name": "id", "required": False, "type": "string", "description": "Resource ID for specific operations"},
                {"name": "data", "required": False, "type": "string", "description": "Data payload for POST/PUT operations"},
            ]

        elif tool_id == "shopify":
            db_tool.method = "GET"
            access_token = request.header.get("access_token") if request.header else None
            shop_domain = request.header.get("shop_domain") if request.header else None

            if not all([access_token, shop_domain]):
                raise HTTPException(status_code=400, detail="Shopify configuration is required (access_token, shop_domain)")

            db_tool.header = {
                "X-Shopify-Access-Token": access_token,
                "Content-Type": "application/json",
            }
            db_tool.webhook = f"https://{shop_domain}.myshopify.com/admin/api/2024-01"
            db_tool.params = [
                {"name": "endpoint", "required": True, "type": "string", "description": "API endpoint (e.g., products, orders, customers)"},
                {"name": "id", "required": False, "type": "string", "description": "Resource ID for specific operations"},
                {"name": "data", "required": False, "type": "string", "description": "Data payload for POST/PUT operations"},
            ]

        elif tool_id == "pipedrive":
            db_tool.method = "GET"
            api_token = request.header.get("api_token") if request.header else None
            domain = request.header.get("domain") if request.header else None

            if not all([api_token, domain]):
                raise HTTPException(status_code=400, detail="Pipedrive configuration is required (api_token, domain)")

            db_tool.header = {
                "Authorization": f"Bearer {api_token}",
                "Content-Type": "application/json",
            }
            db_tool.webhook = f"https://{domain}.pipedrive.com/api/v1"
            db_tool.params = [
                {"name": "endpoint", "required": True, "type": "string", "description": "API endpoint (e.g., persons, deals, organizations)"},
                {"name": "id", "required": False, "type": "string", "description": "Resource ID for specific operations"},
                {"name": "data", "required": False, "type": "string", "description": "Data payload for POST/PUT operations"},
            ]

        elif tool_id == "hubspot":
            db_tool.method = "GET"
            api_key = request.header.get("api_key") if request.header else None

            if not api_key:
                raise HTTPException(status_code=400, detail="HubSpot API key is required")

            db_tool.header = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            db_tool.webhook = "https://api.hubapi.com"
            db_tool.params = [
                {"name": "endpoint", "required": True, "type": "string", "description": "API endpoint (e.g., crm/v3/objects/contacts, crm/v3/objects/deals)"},
                {"name": "id", "required": False, "type": "string", "description": "Resource ID for specific operations"},
                {"name": "data", "required": False, "type": "string", "description": "Data payload for POST/PUT operations"},
            ]

        elif tool_id == "salesforce":
            db_tool.method = "GET"
            access_token = request.header.get("access_token") if request.header else None
            instance_url = request.header.get("instance_url") if request.header else None

            if not all([access_token, instance_url]):
                raise HTTPException(status_code=400, detail="Salesforce configuration is required (access_token, instance_url)")

            db_tool.header = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }
            db_tool.webhook = f"{instance_url}/services/data/v58.0"
            db_tool.params = [
                {"name": "endpoint", "required": True, "type": "string", "description": "API endpoint (e.g., sobjects/Contact, sobjects/Account)"},
                {"name": "id", "required": False, "type": "string", "description": "Record ID for specific operations"},
                {"name": "data", "required": False, "type": "string", "description": "Data payload for POST/PUT operations"},
            ]

        elif tool_id == "google-calendar":
            db_tool.method = "GET"
            access_token = request.header.get("access_token") if request.header else None
            calendar_id = request.header.get("calendar_id") if request.header else None

            if not all([access_token, calendar_id]):
                raise HTTPException(status_code=400, detail="Google Calendar configuration is required (access_token, calendar_id)")

            db_tool.header = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }
            db_tool.webhook = f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}"
            db_tool.params = [
                {"name": "endpoint", "required": True, "type": "string", "description": "API endpoint (e.g., events, freeBusy)"},
                {"name": "id", "required": False, "type": "string", "description": "Event ID for specific operations"},
                {"name": "data", "required": False, "type": "string", "description": "Event data for POST/PUT operations"},
            ]

        elif tool_id == "calendly":
            db_tool.method = "GET"
            api_key = request.header.get("api_key") if request.header else None

            if not api_key:
                raise HTTPException(status_code=400, detail="Calendly API key is required")

            db_tool.header = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            db_tool.webhook = "https://api.calendly.com"
            db_tool.params = [
                {"name": "endpoint", "required": True, "type": "string", "description": "API endpoint (e.g., scheduled_events, event_types)"},
                {"name": "id", "required": False, "type": "string", "description": "Resource ID for specific operations"},
                {"name": "data", "required": False, "type": "string", "description": "Data payload for POST/PUT operations"},
            ]

        elif tool_id == "acuity-scheduling":
            db_tool.method = "GET"
            user_id = request.header.get("user_id") if request.header else None
            api_key = request.header.get("api_key") if request.header else None

            if not all([user_id, api_key]):
                raise HTTPException(status_code=400, detail="Acuity Scheduling configuration is required (user_id, api_key)")

            db_tool.header = {
                "Authorization": f"Basic {api_key}",
                "Content-Type": "application/json",
            }
            db_tool.webhook = f"https://acuityscheduling.com/api/v1/users/{user_id}"
            db_tool.params = [
                {"name": "endpoint", "required": True, "type": "string", "description": "API endpoint (e.g., appointments, appointment-types)"},
                {"name": "id", "required": False, "type": "string", "description": "Resource ID for specific operations"},
                {"name": "data", "required": False, "type": "string", "description": "Data payload for POST/PUT operations"},
            ]

        elif tool_id == "make":
            db_tool.method = "POST"
            webhook_url = request.webhook
            if not webhook_url:
                raise HTTPException(status_code=400, detail="Make.com webhook URL is required")

            db_tool.webhook = webhook_url
            db_tool.params = [
                {"name": "data", "required": True, "type": "string", "description": "Data to send to Make.com webhook"},
            ]

        elif tool_id == "zapier":
            db_tool.method = "POST"
            webhook_url = request.webhook
            if not webhook_url:
                raise HTTPException(status_code=400, detail="Zapier webhook URL is required")

            db_tool.webhook = webhook_url
            db_tool.params = [
                {"name": "data", "required": True, "type": "string", "description": "Data to send to Zapier webhook"},
            ]

        elif tool_id == "custom":
            if not name:
                raise HTTPException(status_code=400, detail="Name is required")
            if not description:
                raise HTTPException(status_code=400, detail="Description is required")
            if not request.webhook:
                raise HTTPException(status_code=400, detail="Webhook URL is required")
            db_tool.webhook = request.webhook
            if request.params is not None:
                db_tool.params = [p.model_dump() for p in request.params]
            if request.header is not None:
                db_tool.header = request.header
            db_tool.method = request.method or "GET"

        if not is_in_db:
            db.add(db_tool)
        await db.commit()
        await db.refresh(db_tool)
        return {"id": str(db_tool.id)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

