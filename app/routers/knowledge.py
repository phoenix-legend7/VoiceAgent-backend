from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import httpx, json

from app.core.database import get_db
from app.models import Knowledge
from app.routers.auth import current_active_user
from app.utils.httpx import get_httpx_headers, httpx_base_url

router = APIRouter()

class GeneratePresignedUrlRequest(BaseModel):
    filename: str

class CreateFileRequest(BaseModel):
    object_key: str
    description: str
    name: str
    file_type: str
    size: int

class DeleteFileRequest(BaseModel):
    id: str

class SetAgentFilesRequest(BaseModel):
    agent_id: str
    files: list[str]
    messages: list[str] = None

@router.post("/generate_presigned_url")
async def generate_presigned_url(
    generate_presigned_url_request: GeneratePresignedUrlRequest,
    _ = Depends(current_active_user)
):
    try:
        async with httpx.AsyncClient() as client:
            headers = get_httpx_headers()
            response = await client.post(f"{httpx_base_url}/knowledge/generate_presigned_url", json=generate_presigned_url_request.model_dump(), headers=headers)
            if response.status_code != 200 and response.status_code != 201:
                raise HTTPException(status_code=response.status_code, detail=response.text or "Unknown Error")
            return response.json()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/create_file")
async def create_file(
    create_file_request: CreateFileRequest,
    db: AsyncSession = Depends(get_db),
    user = Depends(current_active_user)
):
    try:
        async with httpx.AsyncClient() as client:
            headers = get_httpx_headers()
            response = await client.post(f"{httpx_base_url}/knowledge/create_file", data=json.dumps(create_file_request.model_dump()), headers=headers)
            if response.status_code != 200 and response.status_code != 201:
                raise HTTPException(status_code=response.status_code, detail=response.text or "Unknown Error")
            id = create_file_request.object_key.split("/")[1].split("_")[0]
            db_knowledge = Knowledge(
                id = id,
                name = create_file_request.name,
                description = create_file_request.description,
                file_type = create_file_request.file_type,
                size = create_file_request.size,
                created_at = int(datetime.now(timezone.utc).timestamp()),
                user_id = user.id
            )
            db.add(db_knowledge)
            try:
                await db.commit()
                await db.refresh(db_knowledge)
            except Exception as e:
                print(f"Error while saving knowledge: {str(e)}")
            return response.json()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/delete_file")
async def delete_file(
    delete_file_request: DeleteFileRequest,
    db: AsyncSession = Depends(get_db),
    user = Depends(current_active_user)
):
    try:
        id = delete_file_request.id
        result = await db.execute(select(Knowledge).where(Knowledge.id == id, Knowledge.user_id == user.id))
        db_knowledge = result.scalar_one_or_none()
        if not db_knowledge:
            raise HTTPException(status_code=404, detail=f"Not found knowledge {id}")
        async with httpx.AsyncClient() as client:
            headers = get_httpx_headers()
            response = await client.post(f"{httpx_base_url}/knowledge/delete_file", json=delete_file_request.model_dump(), headers=headers)
            if response.status_code != 200 and response.status_code != 201:
                raise HTTPException(status_code=response.status_code, detail=response.text or "Unknown Error")
            try:
                await db.delete(db_knowledge)
                await db.commit()
                await db.refresh(db_knowledge)
            except Exception as e:
                print(f"Failed to delete knowledge: {str(e)}")
            return response.text

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/set_agent_files")
async def set_agent_files(set_agent_files_request: SetAgentFilesRequest, _ = Depends(current_active_user)):
    try:
        async with httpx.AsyncClient() as client:
            headers = get_httpx_headers()
            response = await client.post(f"{httpx_base_url}/knowledge/set_agent_files", json=set_agent_files_request.model_dump(), headers=headers)
            if response.status_code != 200 and response.status_code != 201:
                raise HTTPException(status_code=response.status_code, detail=response.text or "Unknown Error")
            return response.text

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/list_files")
async def list_files_db(db: AsyncSession = Depends(get_db), user = Depends(current_active_user)):
    try:
        result = await db.execute(select(Knowledge).where(Knowledge.user_id == user.id))
        return result.scalars().all()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# @router.get("/list_files")
async def list_files():
    try:
        async with httpx.AsyncClient() as client:
            headers = get_httpx_headers()
            response = await client.get(f"{httpx_base_url}/knowledge/list_files", headers=headers)
            if response.status_code != 200 and response.status_code != 201:
                raise HTTPException(status_code=response.status_code, detail=response.text or "Unknown Error")
            return response.json()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
