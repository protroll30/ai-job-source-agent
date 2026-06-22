from __future__ import annotations

from typing import Optional
from urllib.parse import urlparse

import httpx

from src.utils.logging import get_logger

logger = get_logger(__name__)


async def get_position_via_ats(career_url: str, timeout: int = 30) -> Optional[str]:
    """Try known ATS public JSON APIs before falling back to DOM scraping."""
    from src.discovery.ats_detector import ATS, detect
    ats = detect(career_url)

    handlers = {
        ATS.greenhouse: _greenhouse,
        ATS.lever: _lever,
        ATS.ashby: _ashby,
    }
    handler = handlers.get(ats)
    if handler is None:
        return None

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            return await handler(client, career_url)
    except Exception as exc:
        logger.warning("ATS API call failed (%s): %s", ats, exc)
        return None


async def _greenhouse(client: httpx.AsyncClient, url: str) -> Optional[str]:
    # e.g. https://boards.greenhouse.io/acme → board slug = "acme"
    slug = urlparse(url).path.strip("/").split("/")[0]
    resp = await client.get(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=false")
    resp.raise_for_status()
    jobs = resp.json().get("jobs", [])
    if jobs:
        return jobs[0].get("absolute_url")
    return None


async def _lever(client: httpx.AsyncClient, url: str) -> Optional[str]:
    # e.g. https://jobs.lever.co/acme → company slug = "acme"
    slug = urlparse(url).path.strip("/").split("/")[0]
    resp = await client.get(f"https://api.lever.co/v0/postings/{slug}?mode=json")
    resp.raise_for_status()
    jobs = resp.json()
    if jobs:
        return jobs[0].get("hostedUrl")
    return None


async def _ashby(client: httpx.AsyncClient, url: str) -> Optional[str]:
    # e.g. https://jobs.ashbyhq.com/acme → company slug = "acme"
    slug = urlparse(url).path.strip("/").split("/")[0]
    resp = await client.post(
        "https://api.ashbyhq.com/posting-api/job-board",
        json={"organizationHostedJobsPageName": slug},
    )
    resp.raise_for_status()
    jobs = resp.json().get("jobPostings", [])
    if jobs:
        return jobs[0].get("jobPostingPath") and f"https://jobs.ashbyhq.com/{slug}/{jobs[0]['id']}"
    return None
