"""Kairo Web Research System package."""

from app.tools.web.citations import CitationManager
from app.tools.web.extraction import HTMLTextExtractor, extract_content_from_html
from app.tools.web.fetch import WebFetchTool
from app.tools.web.safety import SSRFViolationError, UnsafeURLError, URLSafetyValidator
from app.tools.web.schemas import (
    FetchResult,
    ResearchContext,
    SearchResult,
    SourceCitation,
    WebFetchArgs,
    WebSearchArgs,
)
from app.tools.web.search import (
    BraveSearchProvider,
    DuckDuckGoSearchProvider,
    MockSearchProvider,
    TavilySearchProvider,
    WebSearchProvider,
    WebSearchTool,
    get_search_provider,
)

__all__ = [
    "BraveSearchProvider",
    "CitationManager",
    "DuckDuckGoSearchProvider",
    "FetchResult",
    "HTMLTextExtractor",
    "MockSearchProvider",
    "ResearchContext",
    "SSRFViolationError",
    "SearchResult",
    "SourceCitation",
    "TavilySearchProvider",
    "URLSafetyValidator",
    "UnsafeURLError",
    "WebFetchArgs",
    "WebFetchTool",
    "WebSearchArgs",
    "WebSearchProvider",
    "WebSearchTool",
    "extract_content_from_html",
    "get_search_provider",
]
