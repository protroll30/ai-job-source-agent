from __future__ import annotations

import re
from typing import Optional
from urllib.parse import urljoin, urlparse

from src.agent.browser import BrowserSession
from src.agent.llm import LLMClient
from src.extraction.ats_clients import get_position_via_ats
from src.models import ExtractionMethod, JobLead, StageResult, StageStatus
from src.utils.logging import get_logger

logger = get_logger(__name__)

# Patterns that indicate a placeholder or generic form rather than a real requisition.
_JUNK_PATTERNS = re.compile(
    r"(register|signup|sign-up|login|apply-general|general-application|#$)",
    re.IGNORECASE,
)


class PositionFinder:
    def __init__(self, llm: LLMClient, browser: BrowserSession, timeout: int = 30):
        self._llm = llm
        self._browser = browser
        self._timeout = timeout

    async def find(self, lead: JobLead) -> JobLead:
        if not lead.career_url:
            lead.extraction_result = StageResult(
                status=StageStatus.failed, error="no career url"
            )
            return lead

        try:
            # 1. Try ATS public JSON API first (fastest, most reliable).
            url = await get_position_via_ats(lead.career_url, self._timeout)
            if url:
                lead.position_url = url
                lead.extraction_result = StageResult(
                    status=StageStatus.ok, method=ExtractionMethod.ats_api
                )
                return lead

            # 2. Render the page and extract links via DOM.
            url = await self._dom_extract(lead.career_url)
            if url:
                lead.position_url = url
                lead.extraction_result = StageResult(
                    status=StageStatus.ok, method=ExtractionMethod.dom
                )
                return lead

            # 3. LLM fallback: let Claude pick from page content.
            url = await self._llm_extract(lead.career_url)
            if url:
                lead.position_url = url
                lead.extraction_result = StageResult(
                    status=StageStatus.ok, method=ExtractionMethod.llm
                )
                return lead

            lead.extraction_result = StageResult(
                status=StageStatus.failed, error="no open position found"
            )
        except Exception as exc:
            logger.error("extraction failed for %s: %s", lead.career_url, exc)
            lead.extraction_result = StageResult(status=StageStatus.failed, error=str(exc))

        return lead

    async def _dom_extract(self, career_url: str) -> Optional[str]:
        html = await self._browser.fetch(career_url)
        from selectolax.parser import HTMLParser
        tree = HTMLParser(html)
        for node in tree.css("a[href]"):
            href = node.attributes.get("href", "")
            absolute = urljoin(career_url, href)
            if self._looks_like_position(absolute):
                return absolute
        return None

    async def _llm_extract(self, career_url: str) -> Optional[str]:
        html = await self._browser.fetch(career_url)
        from selectolax.parser import HTMLParser
        tree = HTMLParser(html)
        links = [
            node.attributes.get("href", "")
            for node in tree.css("a[href]")
            if node.attributes.get("href", "").startswith("http")
        ][:80]

        if not links:
            return None

        prompt = (
            f"From this list of links on a careers page ({career_url}), "
            "pick the URL of one real, active job opening (not a general application form). "
            "Return only the URL or 'none'.\n\n" + "\n".join(links)
        )
        result = await self._llm.complete(prompt)
        result = result.strip()
        return result if result.startswith("http") else None

    def _looks_like_position(self, url: str) -> bool:
        if _JUNK_PATTERNS.search(url):
            return False
        path = urlparse(url).path
        # Must have some path depth suggesting a specific requisition.
        parts = [p for p in path.split("/") if p]
        return len(parts) >= 2
