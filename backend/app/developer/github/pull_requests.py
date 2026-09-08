"""GitHub pull requests and PR diff inspection handlers."""

import logging

from app.developer.git.safety import redact_secrets
from app.developer.github.client import GitHubProvider
from app.developer.schemas import GitDiffResult, GitHubPRInfo

logger = logging.getLogger("kairo.developer.github.prs")

MAX_PR_BODY_CHARS = 4000


def _parse_pr_info(item: dict) -> GitHubPRInfo:
    raw_body = item.get("body") or ""
    is_truncated = len(raw_body) > MAX_PR_BODY_CHARS
    bounded_body = raw_body[:MAX_PR_BODY_CHARS]
    if is_truncated:
        bounded_body += "\n\n[PR BODY TRUNCATED]"

    return GitHubPRInfo(
        number=item.get("number", 0),
        title=item.get("title", ""),
        state=item.get("state", "open"),
        author=item.get("user", {}).get("login", "unknown"),
        source_branch=item.get("head", {}).get("ref", ""),
        target_branch=item.get("base", {}).get("ref", ""),
        created_at=item.get("created_at", ""),
        updated_at=item.get("updated_at", ""),
        body=redact_secrets(bounded_body),
        is_truncated=is_truncated,
        mergeable=item.get("mergeable"),
        html_url=item.get("html_url", ""),
    )


async def list_github_pull_requests(
    provider: GitHubProvider,
    owner: str,
    repo: str,
    state: str = "open",
    limit: int = 20,
) -> list[GitHubPRInfo]:
    """List pull requests in a GitHub repository."""
    clamped_limit = max(1, min(limit, 50))
    params = {"state": state, "per_page": clamped_limit}
    data = await provider.get_json(f"/repos/{owner}/{repo}/pulls", params=params)

    prs: list[GitHubPRInfo] = []
    if isinstance(data, list):
        for item in data:
            prs.append(_parse_pr_info(item))
    return prs


async def get_github_pull_request(
    provider: GitHubProvider,
    owner: str,
    repo: str,
    number: int,
) -> GitHubPRInfo:
    """Get metadata for a specific pull request."""
    data = await provider.get_json(f"/repos/{owner}/{repo}/pulls/{number}")
    return _parse_pr_info(data)


async def get_github_pull_request_diff(
    provider: GitHubProvider,
    owner: str,
    repo: str,
    number: int,
    max_chars: int = 50000,
) -> GitDiffResult:
    """Fetch and bound the unified diff of a GitHub pull request with secret redaction."""
    headers = {"Accept": "application/vnd.github.v3.diff"}
    raw_diff = await provider.get_text(f"/repos/{owner}/{repo}/pulls/{number}", headers_extra=headers)

    total_chars = len(raw_diff)
    is_truncated = False
    diff_content = raw_diff

    if total_chars > max_chars:
        diff_content = (
            raw_diff[:max_chars]
            + f"\n\n[PR DIFF TRUNCATED: Exceeded character limit of {max_chars} chars (Total: {total_chars} chars)]"
        )
        is_truncated = True

    sanitized_diff = redact_secrets(diff_content)

    return GitDiffResult(
        diff_type="commit",
        target=f"PR #{number}",
        diff_content=sanitized_diff,
        is_truncated=is_truncated,
        total_chars=total_chars,
    )
