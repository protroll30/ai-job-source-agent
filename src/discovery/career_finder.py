from __future__ import annotations

import re
from typing import Optional
from urllib.parse import urljoin, urlparse

from src.agent.llm import LLMClient
from src.models import DiscoveryMethod, JobLead, StageResult, StageStatus
from src.utils.http import CachedHttpClient
from src.utils.logging import get_logger

logger = get_logger(__name__)

_CAREER_PATTERNS = re.compile(
    r"(career|careers|jobs|join|work-with-us|life-at|hiring|opportunities)",
    re.IGNORECASE,
)

_COMMON_PATHS = ["/careers", "/jobs", "/join", "/work-with-us", "/about/careers"]

_SITEMAP_LOC = re.compile(r"<loc>\s*(.*?)\s*</loc>", re.IGNORECASE | re.DOTALL)


class CareerFinder:
    def __init__(
        self,
        llm: LLMClient,
        http: CachedHttpClient,
        serp_api_key: str = "",
    ):
        self._llm = llm
        self._http = http
        self._serp_key = serp_api_key

    async def find(self, lead: JobLead) -> JobLead:
        if not lead.company_website:
            lead.discovery_result = StageResult(
                status=StageStatus.failed, error="no company website"
            )
            return lead

        base = lead.company_website.rstrip("/")
        try:
            career_url, method = await self._discover(base)

            if career_url:
                lead.career_url = career_url
                lead.discovery_result = StageResult(status=StageStatus.ok, method=method)
            else:
                lead.discovery_result = StageResult(
                    status=StageStatus.failed, error="career page not found"
                )
        except Exception as exc:
            logger.error("discovery failed for %s: %s", base, exc)
            lead.discovery_result = StageResult(status=StageStatus.failed, error=str(exc))

        return lead

    async def _discover(self, base: str) -> tuple[Optional[str], str]:
        # 1. Heuristic: scan homepage links
        url = await self._heuristic_scan(base)
        if url:
            return url, DiscoveryMethod.heuristic

        # 2. Heuristic: probe common paths
        url = await self._probe_paths(base)
        if url:
            return url, DiscoveryMethod.heuristic

        # 3. Sitemap / robots.txt parse
        url = await self._sitemap_scan(base)
        if url:
            return url, DiscoveryMethod.sitemap

        # 4. LLM semantic match
        url = await self._llm_match(base)
        if url:
            return url, DiscoveryMethod.llm

        # 5. Search engine fallback
        if self._serp_key:
            url = await self._search_fallback(base)
            if url:
                return url, DiscoveryMethod.search

        return None, ""

    async def _heuristic_scan(self, base: str) -> Optional[str]:
        try:
            resp = await self._http.get(base)
        except Exception:
            return None

        return self._pick_career_link(base, resp.text)

    def _pick_career_link(self, base: str, html: str) -> Optional[str]:
        from selectolax.parser import HTMLParser

        tree = HTMLParser(html)
        candidates = []
        for node in tree.css("a[href]"):
            href = node.attributes.get("href", "")
            text = node.text(strip=True)
            if _CAREER_PATTERNS.search(href) or _CAREER_PATTERNS.search(text):
                absolute = urljoin(base, href)
                if urlparse(absolute).netloc:
                    candidates.append(absolute)
        return candidates[0] if candidates else None

    async def _probe_paths(self, base: str) -> Optional[str]:
        for path in _COMMON_PATHS:
            url = base + path
            try:
                resp = await self._http.head(url)
                if resp.status_code < 400:
                    return url
            except Exception:
                continue
        return None

    async def _sitemap_scan(self, base: str) -> Optional[str]:
        sitemap_urls: list[str] = []

        robots_url = urljoin(base + "/", "robots.txt")
        try:
            resp = await self._http.get(robots_url)
            for line in resp.text.splitlines():
                if line.lower().startswith("sitemap:"):
                    sitemap_urls.append(line.split(":", 1)[1].strip())
        except Exception:
            pass

        sitemap_urls.append(urljoin(base + "/", "sitemap.xml"))

        for sitemap_url in sitemap_urls:
            match = await self._career_url_from_sitemap(sitemap_url)
            if match:
                return match
        return None

    async def _career_url_from_sitemap(self, sitemap_url: str) -> Optional[str]:
        try:
            resp = await self._http.get(sitemap_url)
        except Exception:
            return None

        for loc in _SITEMAP_LOC.findall(resp.text):
            loc = loc.strip()
            if _CAREER_PATTERNS.search(loc):
                return loc
        return None

    async def _llm_match(self, base: str) -> Optional[str]:
        try:
            resp = await self._http.get(base)
        except Exception:
            return None

        from selectolax.parser import HTMLParser

        tree = HTMLParser(resp.text)
        links = [
            (node.attributes.get("href", ""), node.text(strip=True))
            for node in tree.css("a[href]")
            if node.attributes.get("href", "").startswith("http")
        ][:60]

        if not links:
            return None

        link_list = "\n".join(f"{text} -> {href}" for href, text in links)
        prompt = (
            f"Given these links from {base}, identify the career/jobs page URL. "
            f"Return only the URL, nothing else, or 'none' if not found.\n\n{link_list}"
        )
        result = await self._llm.complete(prompt)
        result = result.strip()
        return result if result.startswith("http") else None

    async def _search_fallback(self, base: str) -> Optional[str]:
        import httpx

        domain = urlparse(base).netloc
        query = f'site:{domain} "careers" OR "jobs"'
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                "https://serpapi.com/search",
                params={"q": query, "api_key": self._serp_key, "num": 3},
            )
            resp.raise_for_status()
            data = resp.json()
            results = data.get("organic_results", [])
            return results[0]["link"] if results else None
