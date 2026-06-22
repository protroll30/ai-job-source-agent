import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.extraction.ats_clients import get_position_via_ats
from src.extraction.position_finder import PositionFinder
from src.models import ExtractionMethod, JobLead, StageStatus
from src.utils.http import CachedHttpClient

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.mark.asyncio
async def test_greenhouse_api_returns_position():
    fixture = json.loads((FIXTURES_DIR / "greenhouse_jobs.json").read_text())
    career_url = "https://boards.greenhouse.io/acme/jobs"

    mock_resp = MagicMock()
    mock_resp.json.return_value = fixture
    mock_resp.raise_for_status = MagicMock()

    http = MagicMock(spec=CachedHttpClient)
    http.get = AsyncMock(return_value=mock_resp)

    result = await get_position_via_ats(career_url, http)

    assert result == "https://boards.greenhouse.io/acme/jobs/12345"


@pytest.mark.asyncio
async def test_position_finder_uses_ats_first():
    lead = JobLead(
        source_url="https://linkedin.com/jobs/1",
        company_name="Acme",
        career_url="https://boards.greenhouse.io/acme/jobs",
    )
    llm = MagicMock()
    browser = MagicMock()
    http = MagicMock(spec=CachedHttpClient)
    http.is_reachable = AsyncMock(return_value=True)

    with patch(
        "src.extraction.position_finder.get_position_via_ats",
        new=AsyncMock(return_value="https://boards.greenhouse.io/acme/jobs/12345"),
    ):
        finder = PositionFinder(llm=llm, browser=browser, http=http)
        result = await finder.find(lead)

    assert result.position_url == "https://boards.greenhouse.io/acme/jobs/12345"
    assert result.extraction_result.status == StageStatus.ok
    assert result.extraction_result.method == ExtractionMethod.ats_api


@pytest.mark.asyncio
async def test_position_finder_partial_when_no_openings():
    lead = JobLead(
        source_url="https://linkedin.com/jobs/1",
        company_name="Acme",
        career_url="https://careers.acme.com",
    )
    llm = MagicMock()
    browser = MagicMock()
    browser.fetch = AsyncMock(return_value="<html><body></body></html>")
    http = MagicMock(spec=CachedHttpClient)

    with patch(
        "src.extraction.position_finder.get_position_via_ats",
        new=AsyncMock(return_value=None),
    ):
        finder = PositionFinder(llm=llm, browser=browser, http=http)
        result = await finder.find(lead)

    assert result.position_url is None
    assert result.extraction_result.status == StageStatus.partial
