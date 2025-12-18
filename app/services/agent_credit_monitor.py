"""
Service to monitor user credit and automatically stop/start agents based on credit availability.
"""
import httpx
import logging
from sqlalchemy import select
from app.core.database import get_db_background
from app.models import User, Agent
from app.utils.httpx import get_httpx_headers, httpx_base_url

logger = logging.getLogger(__name__)

async def get_agent_status(agent_id: str) -> dict | None:
    """Get the current status of an agent from the external API."""
    try:
        async with httpx.AsyncClient() as client:
            headers = get_httpx_headers()
            response = await client.get(
                f"{httpx_base_url}/agents/{agent_id}",
                headers=headers
            )
            if response.status_code == 200 or response.status_code == 201:
                return response.json()
            else:
                logger.warning(f"Failed to get agent {agent_id} status: {response.status_code} - {response.text}")
                return None
    except Exception as e:
        logger.error(f"Error getting agent {agent_id} status: {str(e)}")
        return None


async def set_agent_status(agent_id: str, status: str) -> bool:
    """Set the status of an agent (active/inactive) via the external API."""
    try:
        async with httpx.AsyncClient() as client:
            headers = get_httpx_headers()
            headers["Content-Type"] = "application/json"
            response = await client.post(
                f"{httpx_base_url}/agents/{agent_id}/status",
                headers=headers,
                json={"status": status}
            )
            if response.status_code == 200 or response.status_code == 201:
                logger.info(f"Successfully set agent {agent_id} status to {status}")
                return True
            else:
                logger.warning(f"Failed to set agent {agent_id} status to {status}: {response.status_code} - {response.text}")
                return False
    except Exception as e:
        logger.error(f"Error setting agent {agent_id} status to {status}: {str(e)}")
        return False


async def monitor_agent_credit():
    """
    Background task to monitor all users' credit and manage their agents.
    - Stops agents when credit is 0 or below
    - Starts agents when credit is available again (if they were stopped due to credit)
    """
    try:
        async with get_db_background() as session:
            # Get all users
            stmt = select(User)
            result = await session.execute(stmt)
            users = result.unique().scalars().all()
            
            processed_count = 0
            stopped_count = 0
            started_count = 0
            
            for user in users:
                try:
                    total_credit = user.total_credit or 0
                    used_credit = user.used_credit or 0
                    available_credit = total_credit - used_credit

                    agent_stmt = select(Agent).where(Agent.user_id == user.id)
                    agent_result = await session.execute(agent_stmt)
                    agents = agent_result.scalars().all()
                    
                    for agent in agents:
                        try:
                            if available_credit <= 0 and not agent.stopped_due_to_credit:
                                success = await set_agent_status(agent.id, "disabled")
                                if success:
                                    agent.stopped_due_to_credit = True
                                    stopped_count += 1
                                    logger.info(f"Stopped agent {agent.id} for user {user.id} due to zero credit")
                            elif available_credit > 0 and agent.stopped_due_to_credit:
                                success = await set_agent_status(agent.id, "active")
                                if success:
                                    agent.stopped_due_to_credit = False
                                    started_count += 1
                                    logger.info(f"Started agent {agent.id} for user {user.id} - credit available")

                            await session.commit()
                            processed_count += 1

                        except Exception as e:
                            logger.error(f"Error processing agent {agent.id} for user {user.id}: {str(e)}")
                            await session.rollback()
                            continue
                    
                except Exception as e:
                    logger.error(f"Error processing user {user.id}: {str(e)}")
                    continue
            
            logger.info(
                f"Credit monitoring completed: {processed_count} agents processed, "
                f"{stopped_count} stopped, {started_count} started"
            )
            return {
                "processed": processed_count,
                "stopped": stopped_count,
                "started": started_count
            }
            
    except Exception as e:
        logger.error(f"Error in monitor_agent_credit: {str(e)}")
        return {"error": str(e)}

