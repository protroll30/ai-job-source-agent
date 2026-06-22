import pytest

from src.models import StageStatus
from src.sources.linkedin.fixture_adapter import FixtureAdapter, FIXTURES


@pytest.fixture
def adapter():
    return FixtureAdapter()


@pytest.mark.asyncio
async def test_fixture_adapter_known_url(adapter):
    url = list(FIXTURES.keys())[0]
    lead = await adapter.fetch(url)
    assert lead.source_result.status == StageStatus.ok
    assert lead.company_name == FIXTURES[url]["company_name"]
    assert lead.company_website == FIXTURES[url]["company_website"]


@pytest.mark.asyncio
async def test_fixture_adapter_unknown_url(adapter):
    lead = await adapter.fetch("https://www.linkedin.com/jobs/view/unknown")
    assert lead.source_result.status == StageStatus.failed
    assert lead.company_name is None
