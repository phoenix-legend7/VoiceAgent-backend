from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from io import BytesIO
import httpx

from app.utils.httpx import get_httpx_headers, httpx_base_url
from app.schemas import AgentGet

router = APIRouter()

class ChatRequest(BaseModel):
    messages: list[dict]
    agent: AgentGet

@router.post("/completions")
async def chat(chat_request: ChatRequest):
    try:
        agent = chat_request.agent.model_dump()
        data = {
            "messages": chat_request.messages,
            "agent": {
                "agent_id": agent.get("id"),
                "agent_config": agent.get("config"),
                "metadata": None,
                "include_metadata_in_prompt": None
            },
            "end_of_session": False
        }
        async with httpx.AsyncClient() as client:
            headers = get_httpx_headers()
            response = await client.post(f"{httpx_base_url}/chat/completions", json=data, headers=headers)
            if response.status_code != 200 and response.status_code != 201:
                raise HTTPException(status_code=response.status_code, detail=response.text or "Unknown Error")

        return StreamingResponse(BytesIO(response.content), media_type=response.headers['Content-Type'])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
