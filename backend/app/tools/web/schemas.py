"""Pydantic schemas and data models for Kairo's Web Research System."""

from datetime import UTC, datetime

from pydantic import BaseModel, Field


class SearchResult(BaseModel):
    """Structured result returned from a web search provider."""

    title: str = Field(..., description="Title of the search result page")
    url: str = Field(..., description="Normalized URL of the search result")
    snippet: str = Field(..., description="Brief snippet or summary of page contents")
    domain: str = Field(..., description="Host domain (e.g. docs.python.org)")
    published_at: str | None = Field(default=None, description="Publication timestamp if available")
    rank: int = Field(default=1, ge=1, description="Ranking position (1-indexed)")

    model_config = {"frozen": True}


class WebSearchArgs(BaseModel):
    """Arguments for the web_search tool."""

    query: str = Field(
        ...,
        min_length=1,
        max_length=300,
        description="Search query terms for live web research",
        examples=["Python 3.12 release notes", "FastAPI dependency injection"],
    )
    limit: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Maximum number of search results to return (1-10)",
    )


class WebFetchArgs(BaseModel):
    """Arguments for the web_fetch tool."""

    url: str = Field(
        ...,
        min_length=8,
        max_length=2000,
        description="Public HTTP or HTTPS URL to fetch content from",
        examples=["https://docs.python.org/3/whatsnew/3.12.html"],
    )


class FetchResult(BaseModel):
    """Result of fetching and extracting content from a public webpage."""

    url: str = Field(..., description="Final fetched URL after safe redirects")
    title: str = Field(default="", description="Page title extracted from HTML")
    text: str = Field(default="", description="Sanitized, extracted plain text content")
    status_code: int = Field(default=200, description="HTTP response status code")
    fetched_at: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat(),
        description="ISO 8601 UTC timestamp of fetch",
    )
    is_cached: bool = Field(default=False, description="Whether result was served from cache")
    content_length: int = Field(default=0, description="Length of extracted text in characters")


class SourceCitation(BaseModel):
    """Traceable citation reference for web-derived information."""

    id: int = Field(..., ge=1, description="Monotonic source ID (e.g. 1 for SOURCE [1])")
    title: str = Field(..., description="Source title")
    url: str = Field(..., description="Verified source URL")
    domain: str = Field(..., description="Source domain name")
    snippet: str = Field(default="", description="Relevant snippet or excerpt")
    published_at: str | None = Field(default=None, description="Publication timestamp if known")


class ResearchContext(BaseModel):
    """Bounded container aggregating research outputs for model reasoning."""

    query: str = Field(..., description="Original research query")
    search_results: list[SearchResult] = Field(default_factory=list)
    citations: list[SourceCitation] = Field(default_factory=list)
    total_chars: int = Field(default=0, description="Total characters in context")
