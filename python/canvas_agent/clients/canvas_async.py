"""Optimized Canvas client with connection pooling and better error handling."""
from __future__ import annotations
import asyncio
import aiohttp
import time
from typing import Dict, Any, Optional, List, Union
from urllib.parse import urljoin
import logging

logger = logging.getLogger(__name__)

class CanvasClientAsync:
    """Async Canvas client with connection pooling and caching."""
    
    def __init__(self, base_url: str, token: str, max_connections: int = 20):
        self.base_url = base_url.rstrip('/')
        self.token = token
        self._session: Optional[aiohttp.ClientSession] = None
        self._max_connections = max_connections
        self._cache: Dict[str, tuple[Any, float]] = {}
        self._cache_ttl = 300  # 5 minutes
        
    async def __aenter__(self):
        await self._ensure_session()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
        
    async def _ensure_session(self):
        if self._session is None or self._session.closed:
            connector = aiohttp.TCPConnector(limit=self._max_connections)
            timeout = aiohttp.ClientTimeout(total=30)
            self._session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers={
                    'Authorization': f'Bearer {self.token}',
                    'Accept': 'application/json',
                    'User-Agent': 'CanvasAgent/2.0'
                }
            )
    
    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
            
    def _cache_key(self, method: str, path: str, params: Optional[Dict] = None) -> str:
        param_str = str(sorted(params.items())) if params else ""
        return f"{method}:{path}:{param_str}"
    
    def _get_cached(self, key: str) -> Optional[Any]:
        if key in self._cache:
            data, timestamp = self._cache[key]
            if time.time() - timestamp < self._cache_ttl:
                return data
            del self._cache[key]
        return None
    
    def _set_cache(self, key: str, data: Any):
        self._cache[key] = (data, time.time())
        # Simple LRU: remove oldest if cache too large
        if len(self._cache) > 1000:
            oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k][1])
            del self._cache[oldest_key]
    
    async def request(self, method: str, path: str, **kwargs) -> Any:
        await self._ensure_session()
        
        # Check cache for GET requests
        if method.upper() == 'GET':
            cache_key = self._cache_key(method, path, kwargs.get('params'))
            cached = self._get_cached(cache_key)
            if cached is not None:
                logger.debug(f"Cache hit for {method} {path}")
                return cached
        
        url = urljoin(self.base_url, path.lstrip('/'))
        
        for attempt in range(3):
            try:
                async with self._session.request(method, url, **kwargs) as response:
                    if response.status == 429:
                        retry_after = int(response.headers.get('Retry-After', 1))
                        await asyncio.sleep(retry_after + attempt)
                        continue
                        
                    response.raise_for_status()
                    data = await response.json()
                    
                    # Cache successful GET requests
                    if method.upper() == 'GET':
                        self._set_cache(cache_key, data)
                    
                    return data
                    
            except aiohttp.ClientError as e:
                if attempt == 2:
                    raise
                await asyncio.sleep(2 ** attempt)
                
        raise Exception(f"Failed after 3 attempts: {method} {path}")
    
    async def get(self, path: str, **kwargs) -> Any:
        return await self.request('GET', path, **kwargs)
    
    async def post(self, path: str, json_data: Optional[Dict] = None, **kwargs) -> Any:
        if json_data:
            kwargs['json'] = json_data
        return await self.request('POST', path, **kwargs)
    
    async def put(self, path: str, json_data: Optional[Dict] = None, **kwargs) -> Any:
        if json_data:
            kwargs['json'] = json_data
        return await self.request('PUT', path, **kwargs)
    
    async def delete(self, path: str, **kwargs) -> Any:
        return await self.request('DELETE', path, **kwargs)

    # Batch operations
    async def batch_get(self, paths: List[str]) -> List[Any]:
        """Execute multiple GET requests concurrently."""
        tasks = [self.get(path) for path in paths]
        return await asyncio.gather(*tasks, return_exceptions=True)
    
    async def get_all_pages(self, path: str, per_page: int = 100) -> List[Any]:
        """Get all pages of a paginated endpoint."""
        all_items = []
        page = 1
        
        while True:
            params = {'page': page, 'per_page': per_page}
            items = await self.get(path, params=params)
            
            if not items or len(items) == 0:
                break
                
            all_items.extend(items)
            
            if len(items) < per_page:
                break
                
            page += 1
            
        return all_items
