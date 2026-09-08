"""Search provider abstraction and WebSearchTool for Kairo."""

from __future__ import annotations

import hashlib
import json
import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

import httpx

from app.core.config import Settings, get_settings
from app.tools.base import BaseTool
from app.tools.permissions import PermissionLevel
from app.tools.web.schemas import SearchResult, WebSearchArgs

if TYPE_CHECKING:
    from app.memory.session import SessionManager

logger = logging.getLogger("kairo.tools.web.search")


class WebSearchProvider(ABC):
    """Abstract base class for all web search providers."""

    @abstractmethod
    async def search(self, query: str, limit: int = 5) -> list[SearchResult]:
        """Perform a web search and return structured search results."""
        ...


class MockSearchProvider(WebSearchProvider):
    """Configurable mock search provider for unit testing and offline development."""

    def __init__(self, predefined_results: list[SearchResult] | None = None) -> None:
        self.predefined_results = predefined_results or []
        self.last_query: str | None = None
        self.last_limit: int | None = None

    async def search(self, query: str, limit: int = 5) -> list[SearchResult]:
        self.last_query = query
        self.last_limit = limit

        if self.predefined_results:
            return self.predefined_results[:limit]

        # Generate deterministic synthetic results for the test query
        return [
            SearchResult(
                title=f"Result 1 for {query}",
                url=f"https://docs.example.com/search?q={query}",
                snippet=f"Official reference and documentation covering {query}.",
                domain="docs.example.com",
                rank=1,
            ),
            SearchResult(
                title=f"Result 2 for {query}",
                url=f"https://news.example.com/articles/{query}",
                snippet=f"Latest updates and community articles regarding {query}.",
                domain="news.example.com",
                rank=2,
            ),
        ][:limit]


class TavilySearchProvider(WebSearchProvider):
    """Search provider using the Tavily Search API."""

    def __init__(self, api_key: str, base_url: str = "https://api.tavily.com") -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    async def search(self, query: str, limit: int = 5) -> list[SearchResult]:
        if not self.api_key:
            raise ValueError("Tavily API key is required.")

        payload = {
            "api_key": self.api_key,
            "query": query,
            "search_depth": "basic",
            "max_results": limit,
            "include_answer": False,
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(f"{self.base_url}/search", json=payload)
            resp.raise_for_status()
            data = resp.json()

        results: list[SearchResult] = []
        raw_results = data.get("results", [])
        for rank, item in enumerate(raw_results[:limit], start=1):
            url = item.get("url", "")
            domain = urlparse(url).netloc or "tavily.com"
            results.append(
                SearchResult(
                    title=item.get("title", ""),
                    url=url,
                    snippet=item.get("content", "")[:300],
                    domain=domain,
                    published_at=item.get("published_date"),
                    rank=rank,
                )
            )
        return results


class BraveSearchProvider(WebSearchProvider):
    """Search provider using the Brave Search API."""

    def __init__(self, api_key: str, base_url: str = "https://api.search.brave.com") -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    async def search(self, query: str, limit: int = 5) -> list[SearchResult]:
        if not self.api_key:
            raise ValueError("Brave Search API key is required.")

        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": self.api_key,
        }
        params = {"q": query, "count": limit}

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{self.base_url}/res/v1/web/search",
                headers=headers,
                params=params,
            )
            resp.raise_for_status()
            data = resp.json()

        results: list[SearchResult] = []
        web_results = data.get("web", {}).get("results", [])
        for rank, item in enumerate(web_results[:limit], start=1):
            url = item.get("url", "")
            domain = urlparse(url).netloc or "brave.com"
            results.append(
                SearchResult(
                    title=item.get("title", ""),
                    url=url,
                    snippet=item.get("description", "")[:300],
                    domain=domain,
                    rank=rank,
                )
            )
        return results


class DuckDuckGoSearchProvider(WebSearchProvider):
    """Zero-credential fallback search provider using DuckDuckGo HTML/Instant API."""

    async def search(self, query: str, limit: int = 5) -> list[SearchResult]:
        # DuckDuckGo instant answer or lite query
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        params = {"q": query, "format": "json", "no_html": "1", "skip_disambig": "1"}

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://api.duckduckgo.com/",
                headers=headers,
                params=params,
            )
            resp.raise_for_status()
            data = resp.json()

        results: list[SearchResult] = []
        rank = 1

        # Check abstract
        if data.get("AbstractURL") and data.get("AbstractText"):
            url = data["AbstractURL"]
            results.append(
                SearchResult(
                    title=data.get("Heading") or query,
                    url=url,
                    snippet=data["AbstractText"][:300],
                    domain=urlparse(url).netloc or "duckduckgo.com",
                    rank=rank,
                )
            )
            rank += 1

        # Check related topics
        for topic in data.get("RelatedTopics", []):
            if rank > limit:
                break
            if isinstance(topic, dict) and topic.get("FirstURL") and topic.get("Text"):
                url = topic["FirstURL"]
                results.append(
                    SearchResult(
                        title=topic.get("Text", "").split(" - ")[0][:100],
                        url=url,
                        snippet=topic["Text"][:300],
                        domain=urlparse(url).netloc or "duckduckgo.com",
                        rank=rank,
                    )
                )
                rank += 1

        return results[:limit]


def get_search_provider(
    provider_name: str | None = None,
    api_key: str | None = None,
    settings: Settings | None = None,
) -> WebSearchProvider | None:
    """Factory creating configured WebSearchProvider, or None if unconfigured."""
    cfg = settings or get_settings()
    name = (provider_name or cfg.WEB_SEARCH_PROVIDER or "").lower().strip()
    key = api_key or cfg.web_search_api_key_str

    if not name:
        return None

    if name == "mock":
        return MockSearchProvider()
    elif name == "tavily":
        return TavilySearchProvider(api_key=key)
    elif name == "brave":
        return BraveSearchProvider(api_key=key)
    elif name in {"duckduckgo", "ddg"}:
        return DuckDuckGoSearchProvider()
    else:
        logger.warning("Unrecognized search provider: '%s'", name)
        return None


class WebSearchTool(BaseTool):
    """Tool allowing Kairo to query the public web for real-time information."""

    name = "web_search"
    description = (
        "Search the public web for current information, documentation, news, or factual queries. "
        "Returns structured search results with title, URL, snippet, and domain."
    )
    permission_level = PermissionLevel.READ
    args_model = WebSearchArgs

    def __init__(
        self,
        provider: WebSearchProvider | None = None,
        session_manager: SessionManager | None = None,
        cache_ttl: int = 900,
        max_results_limit: int = 5,
    ) -> None:
        self.provider = provider
        self.session_manager = session_manager
        self.cache_ttl = cache_ttl
        self.max_results_limit = max_results_limit

    def _get_active_provider(self) -> WebSearchProvider | None:
        if self.provider is not None:
            return self.provider
        return get_search_provider()

    def _cache_key(self, query: str) -> str:
        h = hashlib.sha256(query.strip().lower().encode("utf-8")).hexdigest()[:16]
        return f"kairo:search:{h}"

    async def execute(self, query: str, limit: int = 5) -> dict[str, Any]:
        """Execute web search with validation, deduplication, and caching."""
        clean_query = query.strip()
        if not clean_query:
            return {
                "success": False,
                "error": "Search query cannot be empty.",
                "results": [],
            }

        bounded_limit = max(1, min(limit, self.max_results_limit))

        # Check Redis/SessionManager cache
        sess_mgr = self.session_manager
        if sess_mgr is None:
            try:
                from app.memory.session import get_default_session_manager
                sess_mgr = get_default_session_manager()
            except ImportError:
                sess_mgr = None
        cache_key = self._cache_key(clean_query)
        if sess_mgr is not None:
            cached_str = await sess_mgr.get(cache_key)
            if cached_str:
                try:
                    cached_data = json.loads(cached_str)
                    cached_data["cached"] = True
                    return cached_data
                except Exception:
                    pass

        provider = self._get_active_provider()
        if provider is None:
            logger.info("web_search called but no search provider is configured.")
            return {
                "success": False,
                "status": "unconfigured",
                "message": (
                    "Web search is currently not configured on this instance. "
                    "You must NOT claim that you searched the live web."
                ),
                "results": [],
            }

        try:
            raw_results = await provider.search(query=clean_query, limit=bounded_limit)
        except Exception as exc:
            logger.warning("Web search provider failed for query: %s", exc)
            return {
                "success": False,
                "error": f"Search provider error: {type(exc).__name__}",
                "results": [],
            }

        # Deduplicate URLs and normalize
        seen_urls: set[str] = set()
        deduped: list[SearchResult] = []
        for r in raw_results:
            norm_url = r.url.strip()
            if norm_url not in seen_urls:
                seen_urls.add(norm_url)
                deduped.append(r)

        result_payload = {
            "success": True,
            "query": clean_query,
            "total_results": len(deduped),
            "cached": False,
            "results": [r.model_dump() for r in deduped[:bounded_limit]],
        }

        # Cache result
        if sess_mgr is not None and deduped:
            try:
                await sess_mgr.set(cache_key, json.dumps(result_payload), ttl_seconds=self.cache_ttl)
            except Exception as exc:
                logger.debug("Failed to cache search result: %s", exc)

        return result_payload

    def verify(self, result: Any) -> bool:
        """Verify that web search output matches expected dictionary structure."""
        return isinstance(result, dict) and "results" in result
