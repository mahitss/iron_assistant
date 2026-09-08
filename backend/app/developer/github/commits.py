"""GitHub commits inspection handlers."""

import logging

from app.developer.github.client import GitHubProvider
from app.developer.schemas import GitCommitInfo

logger = logging.getLogger("kairo.developer.github.commits")


async def list_github_commits(
    provider: GitHubProvider,
    owner: str,
    repo: str,
    sha: str | None = None,
    limit: int = 20,
) -> list[GitCommitInfo]:
    """List recent commits on a GitHub repository."""
    clamped_limit = max(1, min(limit, 50))
    params: dict = {"per_page": clamped_limit}
    if sha:
        params["sha"] = sha

    data = await provider.get_json(f"/repos/{owner}/{repo}/commits", params=params)

    commits: list[GitCommitInfo] = []
    if isinstance(data, list):
        for item in data:
            commit_obj = item.get("commit", {})
            author_obj = commit_obj.get("author", {})
            commits.append(
                GitCommitInfo(
                    sha=item.get("sha", "")[:12],
                    author=author_obj.get("name", "Unknown"),
                    date=author_obj.get("date", ""),
                    subject=commit_obj.get("message", "").splitlines()[0]
                    if commit_obj.get("message")
                    else "",
                )
            )
    return commits
