from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import httpx, json
import logging
from bs4 import BeautifulSoup

from app.core.database import get_db
from app.models import Knowledge
from app.routers.auth import current_active_user
from app.utils.httpx import get_httpx_headers, httpx_base_url

logger = logging.getLogger(__name__)

router = APIRouter()

# Helper Functions for URL Scraping
def extract_text_from_html(html: str) -> str:
    """
    Extract clean text from HTML content.
    
    Args:
        html: HTML content as string
        
    Returns:
        Clean text content
    """
    try:
        # Parse HTML with BeautifulSoup
        soup = BeautifulSoup(html, 'lxml')
    except Exception:
        # Fallback to html5lib if lxml fails
        soup = BeautifulSoup(html, 'html5lib')
    
    # Remove script, style, and other non-content elements
    for element in soup(['script', 'style', 'noscript', 'meta', 'link', 'head']):
        element.decompose()
    
    # Get text content
    text = soup.get_text(separator=' ', strip=True)
    
    # Clean up whitespace
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    text = ' '.join(chunk for chunk in chunks if chunk)
    
    return text

async def scrape_url(url: str, timeout: int = 30) -> str:
    """
    Scrape text content from a URL.
    
    Args:
        url: The URL to scrape
        timeout: Request timeout in seconds (default: 30)
        
    Returns:
        Extracted text content
        
    Raises:
        ValueError: If URL is invalid
        httpx.RequestError: If request fails
    """
    # Validate URL format
    if not url.startswith(('http://', 'https://')):
        raise ValueError(f"Invalid URL format: {url}. URL must start with http:// or https://")
    
    # Set headers to mimic a browser request
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
    }
    
    try:
        # Make the request using httpx
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()  # Raise an exception for bad status codes
            
            # Check content type
            content_type = response.headers.get('Content-Type', '').lower()
            if 'text/html' not in content_type and 'text/plain' not in content_type:
                logger.warning(f"Unexpected content type: {content_type} for URL: {url}")
            
            # Extract text from HTML
            text = extract_text_from_html(response.text)
            
            if not text or len(text.strip()) == 0:
                raise ValueError(f"No text content found on the page: {url}")
            
            return text
            
    except httpx.TimeoutException as e:
        raise ValueError(f"Request timeout after {timeout} seconds for URL: {url}") from e
    except httpx.ConnectError as e:
        raise ValueError(f"Connection error while fetching URL: {url}") from e
    except httpx.HTTPStatusError as e:
        raise ValueError(f"HTTP error {e.response.status_code} while fetching URL: {url}") from e
    except httpx.HTTPError as e:
        raise ValueError(f"HTTP error while fetching URL {url}: {str(e)}") from e
    except Exception as e:
        raise ValueError(f"Error scraping URL {url}: {str(e)}") from e

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

class ScrapeUrlRequest(BaseModel):
    url: str = Field(..., description="The URL to scrape", example="https://example.com")
    
    class Config:
        schema_extra = {
            "example": {
                "url": "https://example.com"
            }
        }

class ScrapeUrlResponse(BaseModel):
    text: str = Field(..., description="Extracted text content from the URL")
    
    class Config:
        schema_extra = {
            "example": {
                "text": "Example Domain\nThis domain is for use in illustrative examples..."
            }
        }

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

@router.post("/scrape_url", response_model=ScrapeUrlResponse)
async def scrape_url_endpoint(request: ScrapeUrlRequest):
    """
    Scrape text content from a given URL.
    
    This endpoint fetches the HTML content from the provided URL,
    extracts the text content, and returns it as plain text.
    
    Args:
        request: ScrapeUrlRequest containing the URL to scrape
        
    Returns:
        ScrapeUrlResponse containing the extracted text
        
    Raises:
        HTTPException: If scraping fails or URL is invalid
    """
    try:
        # Validate and scrape the URL
        text = await scrape_url(request.url)
        
        return ScrapeUrlResponse(text=text)
        
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        # Check if it's a connection/timeout/HTTP error (should be 502) or validation error (400)
        error_msg = str(e)
        if any(keyword in error_msg.lower() for keyword in ['timeout', 'connection', 'http error']):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=error_msg
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )
    except Exception as e:
        logger.error(f"Unexpected error scraping URL {request.url}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )
