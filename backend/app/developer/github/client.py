"""GitHub API client provider with token safety and connection pooling."""

import logging
from typing import Any

import httpx

from app.core.config import Settings, get_settings
from app.developer.github.safety import (
    GitHubDisabledError,
    GitHubError,
    handle_github_http_error,
    sanitize_github_error,
)

logger = logging.getLogger("kairo.developer.github.client")


class GitHubProvider:
    """Provides authenticated, rate-limit aware access to GitHub REST API.

    SECURITY:
    - Never leaks the raw token into string representations or logs.
    - Only supports read-only safe endpoints for this phase.
    """

    def __init__(
        self,
        settings: Settings | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self._custom_client = http_client

    def _ensure_enabled(self) -> None:
        if not self.settings.KAIRO_GITHUB_ENABLED:
            raise GitHubDisabledError(
                "GitHub integration is currently disabled in Kairo settings (KAIRO_GITHUB_ENABLED=false)."
            )

    @property
    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Kairo-Assistant/1.0",
        }
        token = self.settings.github_token_str
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    async def get_json(self, path: str, params: dict[str, Any] | None = None) -> Any:
        """Perform a safe GET request to the GitHub API returning JSON."""
        self._ensure_enabled()
        raw_token = self.settings.github_token_str
        url = f"https://api.github.com{path}" if not path.startswith("http") else path

        try:
            if self._custom_client:
                res = await self._custom_client.get(url, headers=self._headers, params=params)
            else:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    res = await client.get(url, headers=self._headers, params=params)

            handle_github_http_error(res, raw_token)
            return res.json()
        except GitHubError:
            raise
        except Exception as exc:
            clean_msg = sanitize_github_error(exc, raw_token)
            raise GitHubError(f"Failed to connect to GitHub API: {clean_msg}") from exc

    async def get_text(self, path: str, headers_extra: dict[str, str] | None = None) -> str:
        """Perform a safe GET request returning text (e.g. diffs)."""
        self._ensure_enabled()
        raw_token = self.settings.github_token_str
        headers = dict(self._headers)
        if headers_extra:
            headers.update(headers_extra)
        url = f"https://api.github.com{path}" if not path.startswith("http") else path

        try:
            if self._custom_client:
                res = await self._custom_client.get(url, headers=headers)
            else:
                async with httpx.AsyncClient(timeout=20.0) as client:
                    res = await client.get(url, headers=headers)

            handle_github_http_error(res, raw_token)
            return res.text
        except GitHubError:
            raise
        except Exception as exc:
            clean_msg = sanitize_github_error(exc, raw_token)
            raise GitHubError(f"Failed to fetch content from GitHub API: {clean_msg}") from exc
