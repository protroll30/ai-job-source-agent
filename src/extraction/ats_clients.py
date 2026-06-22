from __future__ import annotations

from typing import Optional
from urllib.parse import urlparse

import httpx

from src.utils.http import CachedHttpClient
from src.utils.logging import get_logger

logger = get_logger(__name__)


async def get_position_via_ats(
    career_url: str,
    http: CachedHttpClient,
    timeout: int = 30,
) -> Optional[str]:
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
        return await handler(http, career_url, timeout)
    except Exception as exc:
        logger.warning("ATS API call failed (%s): %s", ats, exc)
        return None


async def _greenhouse(http: CachedHttpClient, url: str, timeout: int) -> Optional[str]:
    slug = urlparse(url).path.strip("/").split("/")[0]
    api_url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=false"
    resp = await _fetch_json(http, api_url, timeout)
    jobs = resp.get("jobs", [])
    if jobs:
        return jobs[0].get("absolute_url")
    return None


async def _lever(http: CachedHttpClient, url: str, timeout: int) -> Optional[str]:
    slug = urlparse(url).path.strip("/").split("/")[0]
    api_url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
    jobs = await _fetch_json(http, api_url, timeout)
    if isinstance(jobs, list) and jobs:
        return jobs[0].get("hostedUrl")
    return None


async def _ashby(http: CachedHttpClient, url: str, timeout: int) -> Optional[str]:
    slug = urlparse(url).path.strip("/").split("/")[0]
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(
            "https://api.ashbyhq.com/posting-api/job-board",
            json={"organizationHostedJobsPageName": slug},
        )
        resp.raise_for_status()
        jobs = resp.json().get("jobPostings", [])
    if jobs:
        job_id = jobs[0].get("id")
        if job_id:
            return f"https://jobs.ashbyhq.com/{slug}/{job_id}"
    return None


async def _fetch_json(http: CachedHttpClient, url: str, timeout: int) -> dict | list:
    try:
        resp = await http.get(url)
        return resp.json()
    except Exception:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.json()
