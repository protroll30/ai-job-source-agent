from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from playwright.async_api import async_playwright, Browser, BrowserContext

from src.utils.logging import get_logger

logger = get_logger(__name__)


class BrowserSession:
    def __init__(self, timeout_ms: int = 30_000):
        self._timeout_ms = timeout_ms
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._playwright = None

    async def start(self) -> None:
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=True)
        self._context = await self._browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        )

    async def stop(self) -> None:
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

    async def fetch(self, url: str) -> str:
        if not self._context:
            raise RuntimeError("BrowserSession not started")
        page = await self._context.new_page()
        try:
            await page.goto(url, timeout=self._timeout_ms, wait_until="domcontentloaded")
            return await page.content()
        finally:
            await page.close()

    @asynccontextmanager
    @staticmethod
    async def managed(timeout_ms: int = 30_000) -> AsyncIterator["BrowserSession"]:
        session = BrowserSession(timeout_ms=timeout_ms)
        await session.start()
        try:
            yield session
        finally:
            await session.stop()
