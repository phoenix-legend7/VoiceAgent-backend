import httpx
import os
from fastapi import HTTPException

class HttpClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.client = httpx.AsyncClient()
        self.headers = {}

    async def get(self, url: str, params: dict = None, timeout=100.0):
        try:
            response = await self.client.get(f"{self.base_url}{url}", params=params, headers=self.headers, timeout=timeout)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
        if response.status_code != 200 and response.status_code != 201:
            raise HTTPException(status_code=response.status_code, detail=response.text)
        return response.json()

    async def post(self, url: str, data: dict = None, json: dict = None, content = None, timeout=100.0, stream=False):
        try:
            response = await self.client.post(f"{self.base_url}{url}", data=data, json=json, headers=self.headers, content=content, timeout=timeout)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
        if response.status_code != 200 and response.status_code != 201:
            raise HTTPException(status_code=response.status_code, detail=response.text)
        return response.json() if not stream else response

    async def put(self, url: str, data: dict = None, timeout=100.0):
        try:
            response = await self.client.put(f"{self.base_url}{url}", data=data, headers=self.headers, timeout=timeout)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
        if response.status_code != 200 and response.status_code != 201:
            raise HTTPException(status_code=response.status_code, detail=response.text)
        return response.json()

    async def delete(self, url: str, timeout=100.0):
        try:
            response = await self.client.delete(f"{self.base_url}{url}", headers=self.headers, timeout=timeout)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
        if response.status_code != 200 and response.status_code != 201:
            raise HTTPException(status_code=response.status_code, detail=response.text)
        return response.json()

    async def close(self):
        await self.client.aclose()
    
    def set_auth_token(self, token: str):
        self.headers = {
            "authorization": token
        }

httpx_client = HttpClient(base_url="https://api-west.millis.ai")
httpx_client.set_auth_token(os.getenv("MILLIS_API_PRIVATE_KEY"))
