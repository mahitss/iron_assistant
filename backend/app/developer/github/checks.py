"""GitHub CI and commit check runs inspection handlers."""

import logging

from app.developer.github.client import GitHubProvider
from app.developer.schemas import GitHubCheckInfo

logger = logging.getLogger("kairo.developer.github.checks")


async def get_github_checks(
    provider: GitHubProvider,
    owner: str,
    repo: str,
    ref: str = "main",
) -> list[GitHubCheckInfo]:
    """Inspect CI status and check runs for a commit ref or branch."""
    checks: list[GitHubCheckInfo] = []

    # 1. Fetch check runs
    try:
        data = await provider.get_json(f"/repos/{owner}/{repo}/commits/{ref}/check-runs")
        check_runs = data.get("check_runs", [])
        for cr in check_runs:
            checks.append(
                GitHubCheckInfo(
                    name=cr.get("name", "Unnamed Check"),
                    status=cr.get("status", "unknown"),
                    conclusion=cr.get("conclusion"),
                    html_url=cr.get("html_url", ""),
                    started_at=cr.get("started_at"),
                    completed_at=cr.get("completed_at"),
                )
            )
    except Exception as exc:
        logger.debug("Failed to fetch check runs: %s", exc)

    # 2. If no check runs found, check GitHub Actions workflow runs
    if not checks:
        try:
            act_data = await provider.get_json(
                f"/repos/{owner}/{repo}/actions/runs", params={"branch": ref, "per_page": 5}
            )
            runs = act_data.get("workflow_runs", [])
            for run in runs:
                checks.append(
                    GitHubCheckInfo(
                        name=run.get("name", "Workflow"),
                        status=run.get("status", "unknown"),
                        conclusion=run.get("conclusion"),
                        html_url=run.get("html_url", ""),
                        started_at=run.get("run_started_at"),
                        completed_at=run.get("updated_at"),
                    )
                )
        except Exception as exc:
            logger.debug("Failed to fetch workflow runs: %s", exc)

    return checks
