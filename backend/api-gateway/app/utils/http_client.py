import httpx
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class HTTPClient:
    """Reusable HTTP client for calling backend services"""
    
    def __init__(self, base_url: str, timeout: float = 30.0):
        self.base_url = base_url
        self.timeout = timeout
    
    async def get(self, endpoint: str, headers: Optional[Dict] = None) -> Dict[str, Any]:
        """GET request"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            url = f"{self.base_url}{endpoint}"
            logger.info(f"GET {url}")
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
    
    async def post(
        self,
        endpoint: str,
        json_data: Optional[Dict] = None,
        files: Optional[Dict] = None,
        headers: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """POST request"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            url = f"{self.base_url}{endpoint}"
            logger.info(f"POST {url}")
            response = await client.post(url, json=json_data, files=files, headers=headers)
            response.raise_for_status()
            return response.json()
    
    async def put(
        self,
        endpoint: str,
        json_data: Optional[Dict] = None,
        headers: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """PUT request"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            url = f"{self.base_url}{endpoint}"
            logger.info(f"PUT {url}")
            response = await client.put(url, json=json_data, headers=headers)
            response.raise_for_status()
            return response.json()
    
    async def delete(self, endpoint: str, headers: Optional[Dict] = None) -> Dict[str, Any]:
        """DELETE request"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            url = f"{self.base_url}{endpoint}"
            logger.info(f"DELETE {url}")
            response = await client.delete(url, headers=headers)
            response.raise_for_status()
            return response.json()