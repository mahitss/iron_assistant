"""GitHub repository inspection handlers."""

import logging

from app.developer.github.client import GitHubProvider
from app.developer.schemas import GitHubRepoInfo

logger = logging.getLogger("kairo.developer.github.repos")


async def list_github_repositories(
    provider: GitHubProvider,
    visibility: str = "all",
    limit: int = 20,
) -> list[GitHubRepoInfo]:
    """List repositories accessible to the authenticated user or public repos."""
    clamped_limit = max(1, min(limit, 50))
    data = await provider.get_json("/user/repos", params={"visibility": visibility, "per_page": clamped_limit})

    repos: list[GitHubRepoInfo] = []
    if isinstance(data, list):
        for item in data:
            repos.append(
                GitHubRepoInfo(
                    name=item.get("name", ""),
                    full_name=item.get("full_name", ""),
                    owner=item.get("owner", {}).get("login", ""),
                    description=item.get("description"),
                    visibility=item.get("visibility", "public"),
                    default_branch=item.get("default_branch", "main"),
                    stars=item.get("stargazers_count", 0),
                    forks=item.get("forks_count", 0),
                    html_url=item.get("html_url", ""),
                )
            )
    return repos


async def get_github_repository(
    provider: GitHubProvider,
    owner: str,
    repo: str,
) -> GitHubRepoInfo:
    """Get metadata for a specific GitHub repository."""
    data = await provider.get_json(f"/repos/{owner}/{repo}")
    return GitHubRepoInfo(
        name=data.get("name", repo),
        full_name=data.get("full_name", f"{owner}/{repo}"),
        owner=data.get("owner", {}).get("login", owner),
        description=data.get("description"),
        visibility=data.get("visibility", "public"),
        default_branch=data.get("default_branch", "main"),
        stars=data.get("stargazers_count", 0),
        forks=data.get("forks_count", 0),
        html_url=data.get("html_url", ""),
    )
