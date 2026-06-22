from __future__ import annotations

import asyncio
import json
import os
from typing import List

from src.agent.browser import BrowserSession
from src.config import Config
from src.discovery.career_finder import CareerFinder
from src.extraction.position_finder import PositionFinder
from src.models import JobLead, StageStatus
from src.sources.linkedin.base import LinkedInSource
from src.utils.cache import DiskCache
from src.utils.http import CachedHttpClient
from src.utils.logging import get_logger
from src.utils.rate_limit import RateLimiter

logger = get_logger(__name__)


class Pipeline:
    def __init__(
        self,
        source: LinkedInSource,
        career_finder: CareerFinder,
        position_finder: PositionFinder,
        config: Config,
    ):
        self._source = source
        self._career_finder = career_finder
        self._position_finder = position_finder
        self._config = config
        self._checkpoint: dict[str, dict] = self._load_checkpoint()

    async def run(self, urls: List[str]) -> List[JobLead]:
        sem = asyncio.Semaphore(self._config.concurrency)
        tasks = [self._process(url, sem) for url in urls]
        results = await asyncio.gather(*tasks)
        return list(results)

    async def _process(self, url: str, sem: asyncio.Semaphore) -> JobLead:
        if url in self._checkpoint:
            logger.info("skipping (checkpoint): %s", url)
            return JobLead(**self._checkpoint[url]).finalize()

        async with sem:
            lead = await self._source.fetch(url)

            if lead.source_result.status in (StageStatus.ok, StageStatus.partial):
                lead = await self._career_finder.find(lead)

            if lead.career_url or lead.discovery_result.status == StageStatus.ok:
                lead = await self._position_finder.find(lead)

            lead = lead.finalize()

        self._save_checkpoint(url, lead)
        return lead

    def _load_checkpoint(self) -> dict:
        path = self._config.checkpoint_path
        if os.path.exists(path):
            with open(path) as f:
                return json.load(f)
        return {}

    def _save_checkpoint(self, url: str, lead: JobLead) -> None:
        self._checkpoint[url] = lead.model_dump()
        with open(self._config.checkpoint_path, "w") as f:
            json.dump(self._checkpoint, f, indent=2)
