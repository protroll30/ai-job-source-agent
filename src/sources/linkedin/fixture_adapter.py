from __future__ import annotations

from src.models import JobLead, StageResult, StageStatus
from src.sources.linkedin.base import LinkedInSource

# Hardcoded fixtures for unit tests — never hits the network.
FIXTURES: dict[str, dict] = {
    "https://www.linkedin.com/jobs/view/fixture-1": {
        "company_name": "Acme Corp",
        "company_website": "https://www.acme.com",
    },
    "https://www.linkedin.com/jobs/view/fixture-2": {
        "company_name": "Globex",
        "company_website": "https://www.globex.com",
    },
}


class FixtureAdapter(LinkedInSource):
    def __init__(self, fixtures: dict[str, dict] | None = None):
        self._fixtures = fixtures or FIXTURES

    async def fetch(self, listing_url: str) -> JobLead:
        lead = JobLead(source_url=listing_url)
        data = self._fixtures.get(listing_url)
        if data:
            lead.company_name = data["company_name"]
            lead.company_website = data["company_website"]
            lead.source_result = StageResult(status=StageStatus.ok)
        else:
            lead.source_result = StageResult(
                status=StageStatus.failed,
                error=f"no fixture for {listing_url}",
            )
        return lead
