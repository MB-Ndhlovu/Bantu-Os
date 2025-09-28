""
Base API - Abstract base class for API integrations.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import aiohttp

class BaseAPI(ABC):
    """Base class for API integrations."""
    
    def __init__(self, base_url: str, api_key: Optional[str] = None):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Make an HTTP request to the API."""
        if not self.session:
            raise RuntimeError("API client not initialized. Use async with statement.")
            
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        # Add API key to headers if provided
        request_headers = headers or {}
        if self.api_key:
            request_headers['Authorization'] = f"Bearer {self.api_key}"
        
        async with self.session.request(
            method=method,
            url=url,
            params=params,
            json=json_data,
            headers=request_headers
        ) as response:
            response.raise_for_status()
            return await response.json()
    
    @abstractmethod
    async def test_connection(self) -> bool:
        """Test the API connection."""
        pass
