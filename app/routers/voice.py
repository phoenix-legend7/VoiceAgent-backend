from fastapi import APIRouter

from app.utils.httpx import httpx_client

router = APIRouter()

@router.get("/custom")
async def voice(lang_code: str):
    response = await httpx_client.get("/voices/custom", params={"lang_code": lang_code})
    return response
