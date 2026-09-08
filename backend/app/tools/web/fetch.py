"""Safe WebPage Fetcher tool with SSRF protection, size limits, and sanitization."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from urllib.parse import urljoin, urlparse

import httpx

from app.core.config import Settings, get_settings
from app.tools.base import BaseTool
from app.tools.permissions import PermissionLevel

if TYPE_CHECKING:
    from app.memory.session import SessionManager
from app.tools.web.citations import CitationManager
from app.tools.web.extraction import extract_content_from_html
from app.tools.web.safety import SSRFViolationError, UnsafeURLError, URLSafetyValidator
from app.tools.web.schemas import WebFetchArgs

logger = logging.getLogger("kairo.tools.web.fetch")

# Allowed MIME types for text content extraction
ALLOWED_CONTENT_PREFIXES = (
    "text/html",
    "text/plain",
    "text/markdown",
    "application/xhtml+xml",
    "application/xml",
    "text/xml",
)


class WebFetchTool(BaseTool):
    """Tool for fetching and sanitizing public web pages."""

    name = "web_fetch"
    description = (
        "Fetch the text content of a public webpage by URL. "
        "Returns sanitized text content, title, and source metadata. Does not execute JavaScript."
    )
    permission_level = PermissionLevel.READ
    args_model = WebFetchArgs

    def __init__(
        self,
        citation_manager: CitationManager | None = None,
        session_manager: SessionManager | None = None,
        settings: Settings | None = None,
    ) -> None:
        cfg = settings or get_settings()
        self.citation_manager = citation_manager or CitationManager()
        self.session_manager = session_manager
        self.max_bytes = cfg.WEB_FETCH_MAX_BYTES
        self.timeout = cfg.WEB_FETCH_TIMEOUT_SECONDS
        self.max_redirects = cfg.WEB_FETCH_MAX_REDIRECTS
        self.max_extracted_chars = cfg.WEB_MAX_EXTRACTED_CHARS
        self.cache_ttl = cfg.KAIRO_WEB_CACHE_TTL_SECONDS

    def _cache_key(self, url: str) -> str:
        h = hashlib.sha256(url.strip().lower().encode("utf-8")).hexdigest()[:16]
        return f"kairo:fetch:{h}"

    async def execute(self, url: str) -> dict[str, Any]:
        """Fetch a public webpage safely with SSRF protection, size caps, and text extraction."""
        clean_url = url.strip()

        # 1. SSRF and initial URL validation
        try:
            validated_url = URLSafetyValidator.validate_url(clean_url)
        except (SSRFViolationError, UnsafeURLError) as exc:
            logger.warning("SSRF check failed for fetch target '%s': %s", clean_url, exc)
            return {
                "success": False,
                "url": clean_url,
                "error": f"URL safety validation failed: {exc}",
            }

        # 2. Check cache
        sess_mgr = self.session_manager
        if sess_mgr is None:
            try:
                from app.memory.session import get_default_session_manager

                sess_mgr = get_default_session_manager()
            except ImportError:
                sess_mgr = None
        cache_key = self._cache_key(validated_url)
        if sess_mgr is not None:
            cached_str = await sess_mgr.get(cache_key)
            if cached_str:
                try:
                    cached_payload = json.loads(cached_str)
                    cached_payload["is_cached"] = True
                    return cached_payload
                except Exception:
                    pass

        # 3. Fetch with manual redirect validation and streaming bounds
        current_url = validated_url
        redirect_count = 0
        headers = {
            "User-Agent": "KairoBot/1.0 (+https://github.com/mahitss/iron_assistant)",
            "Accept": "text/html,application/xhtml+xml,text/plain;q=0.9,*/*;q=0.1",
            "Accept-Encoding": "gzip, deflate",
        }

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=False,
                verify=True,
            ) as client:
                while True:
                    resp = await client.get(current_url, headers=headers)

                    # Handle HTTP redirects safely (301, 302, 303, 307, 308)
                    if resp.is_redirect and "location" in resp.headers:
                        redirect_count += 1
                        if redirect_count > self.max_redirects:
                            return {
                                "success": False,
                                "url": current_url,
                                "error": f"Redirect limit exceeded ({self.max_redirects} hops).",
                            }

                        redirect_target = urljoin(current_url, resp.headers["location"])
                        # Re-validate redirect destination against SSRF!
                        try:
                            current_url = URLSafetyValidator.validate_url(redirect_target)
                        except (SSRFViolationError, UnsafeURLError) as exc:
                            logger.warning("SSRF blocked redirect to '%s': %s", redirect_target, exc)
                            return {
                                "success": False,
                                "url": redirect_target,
                                "error": f"Redirect destination blocked by safety policy: {exc}",
                            }
                        continue

                    # Final response reached
                    break

        except httpx.TimeoutException:
            logger.info("Fetch timed out for '%s'", current_url)
            return {
                "success": False,
                "url": current_url,
                "error": f"HTTP request timed out after {self.timeout}s.",
            }
        except httpx.RequestError as exc:
            logger.warning("HTTP request error fetching '%s': %s", current_url, exc)
            return {
                "success": False,
                "url": current_url,
                "error": f"Failed to connect to host: {type(exc).__name__}",
            }
        except Exception as exc:
            logger.exception("Unexpected error fetching '%s'", current_url)
            return {
                "success": False,
                "url": current_url,
                "error": f"Internal fetch error: {type(exc).__name__}",
            }

        if resp.status_code != 200:
            return {
                "success": False,
                "url": current_url,
                "status_code": resp.status_code,
                "error": f"HTTP response status code {resp.status_code}",
            }

        # 4. Content-Type inspection
        content_type = resp.headers.get("content-type", "").lower().split(";")[0].strip()
        if not any(content_type.startswith(prefix) for prefix in ALLOWED_CONTENT_PREFIXES):
            return {
                "success": False,
                "url": current_url,
                "content_type": content_type,
                "error": f"Unsupported Content-Type '{content_type}'. Only text/html and plain text are supported.",
            }

        # 5. Read and enforce size limit
        raw_bytes = resp.content[: self.max_bytes]

        # Decode content safely
        encoding = resp.encoding or "utf-8"
        try:
            html_text = raw_bytes.decode(encoding, errors="replace")
        except Exception:
            html_text = raw_bytes.decode("utf-8", errors="replace")

        # 6. Extract clean text
        title, clean_text = extract_content_from_html(html_text, max_chars=self.max_extracted_chars)
        domain = urlparse(current_url).netloc or "unknown"

        # Register in citation manager
        citation = self.citation_manager.add_source(
            url=current_url,
            title=title or domain,
            snippet=clean_text[:200],
        )

        # 7. Wrap with untrusted data boundary tags for prompt injection protection
        wrapped_content = self.citation_manager.wrap_untrusted_content(
            source_id=citation.id,
            url=current_url,
            title=title or domain,
            domain=domain,
            content=clean_text,
        )

        result_payload = {
            "success": True,
            "url": current_url,
            "title": title,
            "domain": domain,
            "source_id": citation.id,
            "content": wrapped_content,
            "char_count": len(clean_text),
            "status_code": resp.status_code,
            "fetched_at": datetime.now(UTC).isoformat(),
            "is_cached": False,
        }

        # Cache in Redis
        if sess_mgr is not None and clean_text:
            try:
                await sess_mgr.set(cache_key, json.dumps(result_payload), ttl_seconds=self.cache_ttl)
            except Exception as exc:
                logger.debug("Failed to cache page content: %s", exc)

        return result_payload

    def verify(self, result: Any) -> bool:
        """Verify that web fetch output contains expected structure."""
        return isinstance(result, dict) and "url" in result
