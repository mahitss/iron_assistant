"""GitHub API safety, token protection, and clean error sanitization."""

import logging
import re

import httpx

logger = logging.getLogger("kairo.developer.github.safety")


class GitHubError(Exception):
    """Base exception for GitHub API errors with sanitized messages."""


class GitHubAuthenticationError(GitHubError):
    """Raised when authentication fails (401)."""


class GitHubPermissionError(GitHubError):
    """Raised when access is forbidden or rate limits are reached (403)."""


class GitHubNotFoundError(GitHubError):
    """Raised when requested resource does not exist (404)."""


class GitHubDisabledError(GitHubError):
    """Raised when GitHub integration is disabled by configuration."""


def sanitize_github_error(exc: Exception, raw_token: str | None = None) -> str:
    """Strip tokens and sensitive headers from error messages."""
    msg = str(exc)
    if raw_token and raw_token.strip():
        msg = msg.replace(raw_token.strip(), "[REDACTED_TOKEN]")

    # Redact common token patterns
    msg = re.sub(r"gh[pousr]_[A-Za-z0-9_]{20,}", "[REDACTED_TOKEN]", msg)
    msg = re.sub(r"bearer\s+[a-zA-Z0-9_\-\.]+", "Bearer [REDACTED_TOKEN]", msg, flags=re.IGNORECASE)
    msg = re.sub(r"Authorization:\s*[^\s,]+", "Authorization: [REDACTED]", msg, flags=re.IGNORECASE)
    return msg


def handle_github_http_error(response: httpx.Response, raw_token: str | None = None) -> None:
    """Map GitHub HTTP status codes to safe domain exceptions."""
    status = response.status_code
    if status < 400:
        return

    if status == 401:
        raise GitHubAuthenticationError(
            "GitHub authentication failed: Token is invalid, expired, or missing required scope."
        )
    if status == 403:
        rate_remaining = response.headers.get("x-ratelimit-remaining", "")
        if rate_remaining == "0":
            raise GitHubPermissionError("GitHub API rate limit exceeded. Please try again later.")
        raise GitHubPermissionError(
            "GitHub access forbidden: Insufficient permissions to access this repository or resource."
        )
    if status == 404:
        raise GitHubNotFoundError(
            "GitHub resource not found. The repository, issue, or pull request does not exist or is private."
        )

    # General HTTP error
    try:
        data = response.json()
        error_detail = data.get("message", response.text[:200])
    except Exception:
        error_detail = response.text[:200]

    clean_detail = sanitize_github_error(Exception(error_detail), raw_token)
    raise GitHubError(f"GitHub API error ({status}): {clean_detail}")
