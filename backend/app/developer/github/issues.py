"""GitHub issues inspection handlers."""

import logging

from app.developer.git.safety import redact_secrets
from app.developer.github.client import GitHubProvider
from app.developer.schemas import GitHubIssueInfo

logger = logging.getLogger("kairo.developer.github.issues")

MAX_BODY_CHARS = 4000


def _parse_issue_info(item: dict) -> GitHubIssueInfo:
    """Parse raw GitHub issue dictionary into safe GitHubIssueInfo schema."""
    labels = [lbl.get("name", "") for lbl in item.get("labels", []) if isinstance(lbl, dict)]
    raw_body = item.get("body") or ""
    is_truncated = len(raw_body) > MAX_BODY_CHARS
    bounded_body = raw_body[:MAX_BODY_CHARS]
    if is_truncated:
        bounded_body += "\n\n[ISSUE BODY TRUNCATED]"

    return GitHubIssueInfo(
        number=item.get("number", 0),
        title=item.get("title", ""),
        state=item.get("state", "open"),
        author=item.get("user", {}).get("login", "unknown"),
        created_at=item.get("created_at", ""),
        updated_at=item.get("updated_at", ""),
        labels=labels,
        body=redact_secrets(bounded_body),
        is_truncated=is_truncated,
        html_url=item.get("html_url", ""),
    )


async def list_github_issues(
    provider: GitHubProvider,
    owner: str,
    repo: str,
    state: str = "open",
    limit: int = 20,
) -> list[GitHubIssueInfo]:
    """List issues in a GitHub repository."""
    clamped_limit = max(1, min(limit, 50))
    params = {"state": state, "per_page": clamped_limit}
    data = await provider.get_json(f"/repos/{owner}/{repo}/issues", params=params)

    issues: list[GitHubIssueInfo] = []
    if isinstance(data, list):
        for item in data:
            # Exclude pull requests (GitHub API returns PRs in issues endpoint if 'pull_request' key is present)
            if "pull_request" in item:
                continue
            issues.append(_parse_issue_info(item))
    return issues


async def get_github_issue(
    provider: GitHubProvider,
    owner: str,
    repo: str,
    number: int,
) -> GitHubIssueInfo:
    """Get details for a specific GitHub issue."""
    data = await provider.get_json(f"/repos/{owner}/{repo}/issues/{number}")
    return _parse_issue_info(data)
