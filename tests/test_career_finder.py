import pytest
from unittest.mock import AsyncMock, MagicMock

from src.discovery.career_finder import CareerFinder
from src.models import DiscoveryMethod, JobLead, StageStatus


@pytest.mark.asyncio
async def test_heuristic_scan_finds_careers_link():
    html = """
    <html><body>
      <a href="/about">About</a>
      <a href="/careers">Join our team</a>
    </body></html>
    """
    mock_resp = MagicMock()
    mock_resp.text = html

    http = MagicMock()
    http.get = AsyncMock(return_value=mock_resp)
    http.head = AsyncMock()

    finder = CareerFinder(llm=MagicMock(), http=http)
    lead = JobLead(
        source_url="https://linkedin.com/jobs/1",
        company_name="Acme",
        company_website="https://www.acme.com",
    )

    result = await finder.find(lead)

    assert result.career_url == "https://www.acme.com/careers"
    assert result.discovery_result.status == StageStatus.ok
    assert result.discovery_result.method == DiscoveryMethod.heuristic


@pytest.mark.asyncio
async def test_sitemap_scan_finds_careers_url():
    robots = "User-agent: *\nSitemap: https://www.acme.com/sitemap.xml\n"
    sitemap = """
    <?xml version="1.0" encoding="UTF-8"?>
    <urlset>
      <url><loc>https://www.acme.com/about</loc></url>
      <url><loc>https://www.acme.com/careers</loc></url>
    </urlset>
    """
    homepage = "<html><body><a href='/about'>About</a></body></html>"

    async def mock_get(url, **kwargs):
        resp = MagicMock()
        if "robots.txt" in url:
            resp.text = robots
        elif "sitemap.xml" in url:
            resp.text = sitemap
        else:
            resp.text = homepage
        return resp

    http = MagicMock()
    http.get = AsyncMock(side_effect=mock_get)
    http.head = AsyncMock(side_effect=Exception("not found"))

    finder = CareerFinder(llm=MagicMock(), http=http)
    lead = JobLead(
        source_url="https://linkedin.com/jobs/1",
        company_name="Acme",
        company_website="https://www.acme.com",
    )

    result = await finder.find(lead)

    assert result.career_url == "https://www.acme.com/careers"
    assert result.discovery_result.method == DiscoveryMethod.sitemap


@pytest.mark.asyncio
async def test_discovery_fails_without_website():
    finder = CareerFinder(llm=MagicMock(), http=MagicMock())
    lead = JobLead(source_url="https://linkedin.com/jobs/1", company_name="Acme")

    result = await finder.find(lead)

    assert result.discovery_result.status == StageStatus.failed
    assert result.career_url is None
