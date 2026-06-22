from __future__ import annotations

import asyncio
import time
from collections import defaultdict


class RateLimiter:
    """Token-bucket per domain to stay polite."""

    def __init__(self, requests_per_second: float = 2.0):
        self._rps = requests_per_second
        self._last: dict[str, float] = defaultdict(float)
        self._lock = asyncio.Lock()

    async def acquire(self, domain: str) -> None:
        async with self._lock:
            now = time.monotonic()
            wait = (1.0 / self._rps) - (now - self._last[domain])
            if wait > 0:
                await asyncio.sleep(wait)
            self._last[domain] = time.monotonic()
