from __future__ import annotations

import anthropic

from src.utils.logging import get_logger

logger = get_logger(__name__)


class LLMClient:
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6"):
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    async def complete(self, prompt: str, max_tokens: int = 256) -> str:
        # anthropic SDK is sync; run in thread pool to avoid blocking the event loop.
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._sync_complete, prompt, max_tokens)

    def _sync_complete(self, prompt: str, max_tokens: int) -> str:
        message = self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text
