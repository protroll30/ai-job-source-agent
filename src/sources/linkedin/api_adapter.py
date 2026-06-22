from __future__ import annotations

import httpx

from src.models import JobLead, StageResult, StageStatus
from src.sources.linkedin.base import LinkedInSource
from src.utils.logging import get_logger

logger = get_logger(__name__)

PROXYCURL_JOB_ENDPOINT = "https://nubela.co/proxycurl/api/linkedin/job"
PROXYCURL_COMPANY_ENDPOINT = "https://nubela.co/proxycurl/api/linkedin/company"


class ProxycurlAdapter(LinkedInSource):
    def __init__(self, api_key: str):
        self._api_key = api_key
        self._headers = {"Authorization": f"Bearer {api_key}"}

    async def fetch(self, listing_url: str) -> JobLead:
        lead = JobLead(source_url=listing_url)
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                job_data = await self._fetch_job(client, listing_url)
                company_url = job_data.get("company_linkedin_profile_url")
                lead.company_name = job_data.get("company")

                if company_url:
                    company_data = await self._fetch_company(client, company_url)
                    lead.company_website = company_data.get("website")

            lead.source_result = StageResult(status=StageStatus.ok)
        except Exception as exc:
            logger.error("source stage failed for %s: %s", listing_url, exc)
            lead.source_result = StageResult(status=StageStatus.failed, error=str(exc))

        return lead

    async def _fetch_job(self, client: httpx.AsyncClient, url: str) -> dict:
        resp = await client.get(
            PROXYCURL_JOB_ENDPOINT,
            headers=self._headers,
            params={"url": url},
        )
        resp.raise_for_status()
        return resp.json()

    async def _fetch_company(self, client: httpx.AsyncClient, url: str) -> dict:
        resp = await client.get(
            PROXYCURL_COMPANY_ENDPOINT,
            headers=self._headers,
            params={"url": url},
        )
        resp.raise_for_status()
        return resp.json()
