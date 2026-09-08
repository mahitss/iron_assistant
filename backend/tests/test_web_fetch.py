"""Tests for Safe WebPage Fetcher Tool (WebFetchTool)."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.memory.session import SessionManager
from app.tools.web.citations import CitationManager
from app.tools.web.fetch import WebFetchTool


@pytest.fixture
def session_manager():
    return SessionManager(redis_url=None)


@pytest.fixture
def citation_manager():
    return CitationManager()


async def test_web_fetch_tool_success(citation_manager, session_manager):
    """WebFetchTool fetches page, extracts clean text, and wraps with untrusted tags."""
    sample_html = """
    <html>
      <head><title>Test Article Title</title></head>
      <body>
        <script>alert(1);</script>
        <h1>Article Heading</h1>
        <p>This is the verified factual content from the public web.</p>
      </body>
    </html>
    """
    mock_resp = httpx.Response(
        status_code=200,
        headers={"content-type": "text/html; charset=utf-8"},
        content=sample_html.encode("utf-8"),
        request=httpx.Request("GET", "https://example.com/article"),
    )

    with patch("socket.getaddrinfo") as mock_dns:
        mock_dns.return_value = [(2, 1, 6, "", ("93.184.216.34", 443))]
        with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_resp

            tool = WebFetchTool(
                citation_manager=citation_manager,
                session_manager=session_manager,
            )
            res = await tool.execute(url="https://example.com/article")

            assert res["success"] is True
            assert res["title"] == "Test Article Title"
            assert "Article Heading" in res["content"]
            assert "verified factual content" in res["content"]
            assert '<web_source id="1"' in res["content"]
            assert "UNTRUSTED EXTERNAL DATA" in res["content"]
            assert res["char_count"] > 0


async def test_web_fetch_ssrf_blocked():
    """Attempt to fetch private or loopback IP is blocked immediately before sending HTTP request."""
    tool = WebFetchTool()
    res = await tool.execute(url="http://127.0.0.1:8000/admin")

    assert res["success"] is False
    assert "safety validation failed" in res["error"].lower()
    assert "loopback" in res["error"].lower()


async def test_web_fetch_redirect_to_private_blocked(citation_manager):
    """Redirect from public host to private IP must be caught and blocked."""
    redirect_resp = httpx.Response(
        status_code=302,
        headers={"location": "http://192.168.1.1/admin/router"},
        request=httpx.Request("GET", "https://example.com/redirect"),
    )

    with patch("socket.getaddrinfo") as mock_dns:
        mock_dns.return_value = [(2, 1, 6, "", ("93.184.216.34", 443))]
        with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = redirect_resp

            tool = WebFetchTool(citation_manager=citation_manager)
            res = await tool.execute(url="https://example.com/redirect")

            assert res["success"] is False
            assert "redirect destination blocked" in res["error"].lower()
            assert "private" in res["error"].lower()


async def test_web_fetch_redirect_limit_exceeded(citation_manager):
    """Exceeding max redirect hops returns error."""
    loop_resp = httpx.Response(
        status_code=301,
        headers={"location": "https://example.com/loop"},
        request=httpx.Request("GET", "https://example.com/loop"),
    )

    with patch("socket.getaddrinfo") as mock_dns:
        mock_dns.return_value = [(2, 1, 6, "", ("93.184.216.34", 443))]
        with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = loop_resp

            tool = WebFetchTool(citation_manager=citation_manager)
            res = await tool.execute(url="https://example.com/loop")

            assert res["success"] is False
            assert "redirect limit exceeded" in res["error"].lower()


async def test_web_fetch_unsupported_content_type(citation_manager):
    """Unsupported content types such as PDF or images must be rejected."""
    pdf_resp = httpx.Response(
        status_code=200,
        headers={"content-type": "application/pdf"},
        content=b"%PDF-1.4 ... binary data",
        request=httpx.Request("GET", "https://example.com/doc.pdf"),
    )

    with patch("socket.getaddrinfo") as mock_dns:
        mock_dns.return_value = [(2, 1, 6, "", ("93.184.216.34", 443))]
        with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = pdf_resp

            tool = WebFetchTool(citation_manager=citation_manager)
            res = await tool.execute(url="https://example.com/doc.pdf")

            assert res["success"] is False
            assert "unsupported content-type" in res["error"].lower()


async def test_web_fetch_timeout(citation_manager):
    """HTTP timeout must be caught and reported as structured error."""
    with patch("socket.getaddrinfo") as mock_dns:
        mock_dns.return_value = [(2, 1, 6, "", ("93.184.216.34", 443))]
        with patch.object(httpx.AsyncClient, "get", side_effect=httpx.TimeoutException("Timed out")):
            tool = WebFetchTool(citation_manager=citation_manager)
            res = await tool.execute(url="https://example.com/slow")

            assert res["success"] is False
            assert "timed out" in res["error"].lower()


async def test_web_fetch_caching(citation_manager, session_manager):
    """Second fetch for same URL returns cached content."""
    mock_resp = httpx.Response(
        status_code=200,
        headers={"content-type": "text/html"},
        content=b"<html><body><p>Cache test content</p></body></html>",
        request=httpx.Request("GET", "https://example.com/cache"),
    )

    with patch("socket.getaddrinfo") as mock_dns:
        mock_dns.return_value = [(2, 1, 6, "", ("93.184.216.34", 443))]
        with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_resp

            tool = WebFetchTool(
                citation_manager=citation_manager,
                session_manager=session_manager,
            )

            res1 = await tool.execute(url="https://example.com/cache")
            assert res1["success"] is True
            assert res1["is_cached"] is False

            res2 = await tool.execute(url="https://example.com/cache")
            assert res2["success"] is True
            assert res2["is_cached"] is True
