"""Git branch and bounded commit history inspection."""

import logging

from app.core.config import Settings, get_settings
from app.developer.git.repository import run_git_exec
from app.developer.git.safety import validate_repo_path
from app.developer.schemas import GitBranchInfo, GitCommitInfo

logger = logging.getLogger("kairo.developer.git.history")


async def inspect_git_branches(repo_path: str, settings: Settings | None = None) -> GitBranchInfo:
    """Inspect local and remote branches in a validated repository."""
    cfg = settings or get_settings()
    validated_path = validate_repo_path(repo_path, cfg.get_approved_repo_roots())

    # Get current branch
    code_cur, cur_out, _ = await run_git_exec(["rev-parse", "--abbrev-ref", "HEAD"], cwd=validated_path)
    current_branch = cur_out.strip() if code_cur == 0 else "HEAD"

    # Get local branches
    code_local, local_out, _ = await run_git_exec(["branch", "--list", "--format=%(refname:short)"], cwd=validated_path)
    local_branches = [b.strip() for b in local_out.splitlines() if b.strip()] if code_local == 0 else []

    # Get remote branches
    code_remote, remote_out, _ = await run_git_exec(["branch", "-r", "--format=%(refname:short)"], cwd=validated_path)
    remote_branches = [b.strip() for b in remote_out.splitlines() if b.strip() and not b.endswith("/HEAD")] if code_remote == 0 else []

    return GitBranchInfo(
        current_branch=current_branch,
        local_branches=local_branches,
        remote_branches=remote_branches,
    )


async def inspect_git_log(
    repo_path: str,
    limit: int = 10,
    settings: Settings | None = None,
) -> list[GitCommitInfo]:
    """Inspect bounded commit history.

    SECURITY:
    - Limit clamped between 1 and KAIRO_MAX_GIT_LOG_ENTRIES (default max 50).
    - Returns bounded metadata only (sha, author, date, subject).
    """
    cfg = settings or get_settings()
    validated_path = validate_repo_path(repo_path, cfg.get_approved_repo_roots())

    max_allowed = cfg.KAIRO_MAX_GIT_LOG_ENTRIES
    clamped_limit = max(1, min(limit, max_allowed))

    # Use unit-separator %x1f for delimiter
    code, stdout, stderr = await run_git_exec(
        ["log", f"-n{clamped_limit}", "--format=%H%x1f%an%x1f%ad%x1f%s", "--date=short"],
        cwd=validated_path,
    )

    if code != 0:
        logger.warning("Git log returned code %d: %s", code, stderr)
        return []

    commits: list[GitCommitInfo] = []
    for line in stdout.splitlines():
        if not line:
            continue
        parts = line.split("\x1f")
        if len(parts) >= 4:
            commits.append(
                GitCommitInfo(
                    sha=parts[0].strip(),
                    author=parts[1].strip(),
                    date=parts[2].strip(),
                    subject=parts[3].strip(),
                )
            )

    return commits
