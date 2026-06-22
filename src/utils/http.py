from __future__ import annotations

from typing import Optional
from urllib.parse import urlparse

import httpx

from src.utils.cache import DiskCache
from src.utils.rate_limit import RateLimiter


class CachedHttpClient:
    """httpx wrapper with per-URL disk cache and per-domain rate limiting."""

    def __init__(
        self,
        cache: Optional[DiskCache] = None,
        rate_limiter: Optional[RateLimiter] = None,
        timeout: int = 30,
    ):
        self._cache = cache
        self._rate_limiter = rate_limiter
        self._timeout = timeout

    async def get(self, url: str, *, use_cache: bool = True) -> httpx.Response:
        if use_cache and self._cache:
            cached = self._cache.get(url)
            if cached is not None:
                return httpx.Response(
                    status_code=cached["status_code"],
                    text=cached.get("text", ""),
                    request=httpx.Request("GET", url),
                )

        if self._rate_limiter:
            domain = urlparse(url).netloc
            await self._rate_limiter.acquire(domain)

        async with httpx.AsyncClient(timeout=self._timeout, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()

        if use_cache and self._cache:
            self._cache.set(
                url,
                {"status_code": resp.status_code, "text": resp.text},
            )
        return resp

    async def head(self, url: str) -> httpx.Response:
        if self._rate_limiter:
            domain = urlparse(url).netloc
            await self._rate_limiter.acquire(domain)

        async with httpx.AsyncClient(timeout=self._timeout, follow_redirects=True) as client:
            return await client.head(url)

    async def is_reachable(self, url: str) -> bool:
        try:
            resp = await self.head(url)
            if resp.status_code == 405:
                resp = await self.get(url, use_cache=False)
            return resp.status_code < 400
        except Exception:
            return False
