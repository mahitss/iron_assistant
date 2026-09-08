"""Unit tests for GitHub API provider, handlers, and safety."""

import httpx
import pytest
from pydantic import SecretStr

from app.core.config import Settings
from app.developer.github.checks import get_github_checks
from app.developer.github.client import GitHubProvider
from app.developer.github.issues import list_github_issues
from app.developer.github.pull_requests import (
    get_github_pull_request_diff,
    list_github_pull_requests,
)
from app.developer.github.repositories import get_github_repository, list_github_repositories
from app.developer.github.safety import (
    GitHubAuthenticationError,
    GitHubDisabledError,
    GitHubNotFoundError,
    GitHubPermissionError,
)


@pytest.fixture
def github_settings():
    return Settings(
        KAIRO_GITHUB_ENABLED=True,
        KAIRO_GITHUB_TOKEN=SecretStr("ghp_SecretMockTokenForTests12345"),
        KAIRO_MAX_DIFF_CHARS=1000,
    )


def _create_mock_github_client(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


@pytest.mark.asyncio
async def test_github_disabled_error():
    """Ensure accessing GitHub when disabled raises GitHubDisabledError."""
    settings = Settings(KAIRO_GITHUB_ENABLED=False)
    provider = GitHubProvider(settings=settings)
    with pytest.raises(GitHubDisabledError):
        await provider.get_json("/user/repos")


@pytest.mark.asyncio
async def test_github_list_and_get_repositories(github_settings: Settings):
    """Verify repository listing and detail fetching with safe metadata."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/user/repos":
            return httpx.Response(
                200,
                json=[
                    {
                        "name": "iron_assistant",
                        "full_name": "owner/iron_assistant",
                        "owner": {"login": "owner"},
                        "description": "Kairo AI",
                        "visibility": "public",
                        "default_branch": "main",
                        "stargazers_count": 42,
                        "forks_count": 5,
                        "html_url": "https://github.com/owner/iron_assistant",
                    }
                ],
            )
        if request.url.path == "/repos/owner/iron_assistant":
            return httpx.Response(
                200,
                json={
                    "name": "iron_assistant",
                    "full_name": "owner/iron_assistant",
                    "owner": {"login": "owner"},
                    "description": "Kairo AI",
                    "visibility": "public",
                    "default_branch": "main",
                    "stargazers_count": 42,
                    "forks_count": 5,
                    "html_url": "https://github.com/owner/iron_assistant",
                },
            )
        return httpx.Response(404)

    client = _create_mock_github_client(handler)
    provider = GitHubProvider(settings=github_settings, http_client=client)

    repos = await list_github_repositories(provider)
    assert len(repos) == 1
    assert repos[0].name == "iron_assistant"
    assert repos[0].stars == 42

    repo = await get_github_repository(provider, "owner", "iron_assistant")
    assert repo.full_name == "owner/iron_assistant"
    assert repo.default_branch == "main"


@pytest.mark.asyncio
async def test_github_issues_and_prs(github_settings: Settings):
    """Verify issues and PR listing and diff inspection with secret redaction."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/repos/owner/repo/issues":
            return httpx.Response(
                200,
                json=[
                    {
                        "number": 1,
                        "title": "Bug in auth",
                        "state": "open",
                        "user": {"login": "coder"},
                        "created_at": "2026-09-08T12:00:00Z",
                        "updated_at": "2026-09-08T12:00:00Z",
                        "labels": [{"name": "bug"}],
                        "body": "Found key sk-1234567890abcdef1234567890 in log",
                    }
                ],
            )
        if request.url.path == "/repos/owner/repo/pulls":
            return httpx.Response(
                200,
                json=[
                    {
                        "number": 10,
                        "title": "Fix bug",
                        "state": "open",
                        "user": {"login": "dev"},
                        "head": {"ref": "fix-branch"},
                        "base": {"ref": "main"},
                        "created_at": "2026-09-08T12:00:00Z",
                        "updated_at": "2026-09-08T12:00:00Z",
                        "body": "Fixes issue #1",
                        "mergeable": True,
                    }
                ],
            )
        if request.url.path == "/repos/owner/repo/pulls/10":
            if request.headers.get("Accept") == "application/vnd.github.v3.diff":
                return httpx.Response(
                    200, text="--- a/file.py\n+++ b/file.py\n+token = 'ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ012345'"
                )
            return httpx.Response(200, json={"number": 10, "title": "Fix bug", "state": "open"})
        return httpx.Response(404)

    client = _create_mock_github_client(handler)
    provider = GitHubProvider(settings=github_settings, http_client=client)

    issues = await list_github_issues(provider, "owner", "repo")
    assert len(issues) == 1
    assert issues[0].number == 1
    # Check secret redaction in body
    assert "[REDACTED_API_KEY]" in issues[0].body

    prs = await list_github_pull_requests(provider, "owner", "repo")
    assert len(prs) == 1
    assert prs[0].source_branch == "fix-branch"

    diff = await get_github_pull_request_diff(provider, "owner", "repo", 10)
    assert diff.diff_type == "commit"
    assert "[REDACTED_GITHUB_TOKEN]" in diff.diff_content


@pytest.mark.asyncio
async def test_github_checks(github_settings: Settings):
    """Verify GitHub CI checks retrieval."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "check_runs": [
                    {
                        "name": "backend-tests",
                        "status": "completed",
                        "conclusion": "success",
                        "html_url": "https://github.com/owner/repo/runs/123",
                    }
                ]
            },
        )

    client = _create_mock_github_client(handler)
    provider = GitHubProvider(settings=github_settings, http_client=client)

    checks = await get_github_checks(provider, "owner", "repo", "main")
    assert len(checks) == 1
    assert checks[0].name == "backend-tests"
    assert checks[0].conclusion == "success"


@pytest.mark.asyncio
async def test_github_error_mappings_and_token_isolation(github_settings: Settings):
    """Verify 401, 403, 404 mapping and ensure token is never leaked in errors."""

    def handler_401(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            401, json={"message": f"Bad credentials with {request.headers.get('Authorization')}"}
        )

    client_401 = _create_mock_github_client(handler_401)
    provider_401 = GitHubProvider(settings=github_settings, http_client=client_401)

    with pytest.raises(GitHubAuthenticationError) as exc_info:
        await provider_401.get_json("/user/repos")
    # Verify raw token is NOT in exception text
    assert "ghp_SecretMockTokenForTests12345" not in str(exc_info.value)

    def handler_403(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            403, headers={"x-ratelimit-remaining": "0"}, json={"message": "Rate limit exceeded"}
        )

    client_403 = _create_mock_github_client(handler_403)
    provider_403 = GitHubProvider(settings=github_settings, http_client=client_403)
    with pytest.raises(GitHubPermissionError) as exc_info_403:
        await provider_403.get_json("/user/repos")
    assert "rate limit exceeded" in str(exc_info_403.value).lower()

    def handler_404(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"message": "Not Found"})

    client_404 = _create_mock_github_client(handler_404)
    provider_404 = GitHubProvider(settings=github_settings, http_client=client_404)
    with pytest.raises(GitHubNotFoundError):
        await provider_404.get_json("/repos/owner/nonexistent")
