import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.utils.cache import DiskCache
from src.utils.http import CachedHttpClient
from src.utils.rate_limit import RateLimiter


@pytest.mark.asyncio
async def test_cached_http_returns_cached_response(tmp_path):
    cache = DiskCache(str(tmp_path))
    cache.set("https://example.com", {"status_code": 200, "text": "<html>cached</html>"})

    http = CachedHttpClient(cache=cache)
    resp = await http.get("https://example.com")

    assert resp.status_code == 200
    assert resp.text == "<html>cached</html>"


@pytest.mark.asyncio
async def test_cached_http_fetches_and_stores(tmp_path):
    cache = DiskCache(str(tmp_path))
    http = CachedHttpClient(cache=cache, rate_limiter=RateLimiter(10))

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = "<html>live</html>"

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client

        resp = await http.get("https://example.com/page", use_cache=True)

    assert resp.text == "<html>live</html>"
    assert cache.get("https://example.com/page") is not None
