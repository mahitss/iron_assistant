"""Tests for Web Search Provider Abstraction and WebSearchTool."""

import pytest

from app.memory.session import SessionManager
from app.tools.web.schemas import SearchResult
from app.tools.web.search import MockSearchProvider, WebSearchTool


@pytest.fixture
def session_manager():
    return SessionManager(redis_url=None)


@pytest.fixture
def mock_provider():
    predefined = [
        SearchResult(
            title="Python 3.12 What's New",
            url="https://docs.python.org/3/whatsnew/3.12.html",
            snippet="Documentation on all new features in Python 3.12.",
            domain="docs.python.org",
            rank=1,
        ),
        SearchResult(
            title="FastAPI Web Framework",
            url="https://fastapi.tiangolo.com/",
            snippet="Modern high-performance web framework for Python.",
            domain="fastapi.tiangolo.com",
            rank=2,
        ),
        SearchResult(
            title="Duplicate URL Result",
            url="https://docs.python.org/3/whatsnew/3.12.html",  # duplicate URL
            snippet="Alternative mirror with same URL.",
            domain="docs.python.org",
            rank=3,
        ),
    ]
    return MockSearchProvider(predefined_results=predefined)


async def test_mock_search_provider(mock_provider):
    """Mock search provider returns structured search results."""
    results = await mock_provider.search("python", limit=2)
    assert len(results) == 2
    assert results[0].title == "Python 3.12 What's New"
    assert results[0].domain == "docs.python.org"


async def test_web_search_tool_success(mock_provider, session_manager):
    """WebSearchTool executes query and returns structured result payload."""
    tool = WebSearchTool(provider=mock_provider, session_manager=session_manager)
    res = await tool.execute(query="python updates", limit=5)

    assert res["success"] is True
    assert res["query"] == "python updates"
    assert res["total_results"] == 2  # duplicate was stripped!
    assert res["results"][0]["url"] == "https://docs.python.org/3/whatsnew/3.12.html"
    assert res["results"][1]["url"] == "https://fastapi.tiangolo.com/"


async def test_web_search_tool_deduplicates_urls(mock_provider):
    """WebSearchTool deduplicates identical URLs in results."""
    tool = WebSearchTool(provider=mock_provider)
    res = await tool.execute(query="python", limit=5)
    urls = [r["url"] for r in res["results"]]
    assert len(urls) == len(set(urls))


async def test_web_search_tool_empty_query():
    """Empty or whitespace search query returns error."""
    tool = WebSearchTool(provider=MockSearchProvider())
    res = await tool.execute(query="   ")
    assert res["success"] is False
    assert "cannot be empty" in res["error"].lower()


async def test_web_search_tool_limit_bounds(mock_provider):
    """Limit bounds are enforced by WebSearchTool."""
    tool = WebSearchTool(provider=mock_provider, max_results_limit=1)
    res = await tool.execute(query="python", limit=10)
    assert len(res["results"]) == 1


async def test_web_search_unconfigured_provider():
    """Unconfigured search provider returns graceful fallback message."""
    tool = WebSearchTool(provider=None)
    res = await tool.execute(query="latest news")
    assert res["success"] is False
    assert res["status"] == "unconfigured"
    assert "must not claim" in res["message"].lower()
    assert res["results"] == []


async def test_web_search_provider_error_handled():
    """Provider exception is caught and returns structured error."""

    class BrokenProvider(MockSearchProvider):
        async def search(self, query: str, limit: int = 5):
            raise ConnectionError("Network unreachable")

    tool = WebSearchTool(provider=BrokenProvider())
    res = await tool.execute(query="test query")
    assert res["success"] is False
    assert "ConnectionError" in res["error"]


async def test_web_search_caching(mock_provider, session_manager):
    """Subsequent search queries return cached results."""
    tool = WebSearchTool(provider=mock_provider, session_manager=session_manager)

    # First call - cache miss
    res1 = await tool.execute(query="caching test", limit=2)
    assert res1["cached"] is False

    # Second call - cache hit
    res2 = await tool.execute(query="caching test", limit=2)
    assert res2["cached"] is True
    assert res2["results"] == res1["results"]
