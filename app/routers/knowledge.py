from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import httpx

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
async def generate_presigned_url(generate_presigned_url_request: GeneratePresignedUrlRequest):
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
async def create_file(create_file_request: CreateFileRequest):
    try:
        async with httpx.AsyncClient() as client:
            headers = get_httpx_headers()
            response = await client.post(f"{httpx_base_url}/knowledge/create_file", json=create_file_request.model_dump(), headers=headers)
            if response.status_code != 200 and response.status_code != 201:
                raise HTTPException(status_code=response.status_code, detail=response.text or "Unknown Error")
            return response.text

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/delete_file")
async def delete_file(delete_file_request: DeleteFileRequest):
    try:
        async with httpx.AsyncClient() as client:
            headers = get_httpx_headers()
            response = await client.post(f"{httpx_base_url}/knowledge/delete_file", json=delete_file_request.model_dump(), headers=headers)
            if response.status_code != 200 and response.status_code != 201:
                raise HTTPException(status_code=response.status_code, detail=response.text or "Unknown Error")
            return response.text

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/set_agent_files")
async def set_agent_files(set_agent_files_request: SetAgentFilesRequest):
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
