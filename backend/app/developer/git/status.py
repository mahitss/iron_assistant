"""Safe, bounded Git working tree status inspection."""

import logging

from app.core.config import Settings, get_settings
from app.developer.git.repository import run_git_exec
from app.developer.git.safety import validate_repo_path
from app.developer.schemas import GitStatusResult

logger = logging.getLogger("kairo.developer.git.status")


async def inspect_git_status(repo_path: str, settings: Settings | None = None) -> GitStatusResult:
    """Inspect the working tree status of a validated repository.

    SECURITY:
    - Path validated against approved roots.
    - Ignored files and secret files excluded.
    - Zero file content exposed in status.
    """
    cfg = settings or get_settings()
    validated_path = validate_repo_path(repo_path, cfg.get_approved_repo_roots())

    code, stdout, stderr = await run_git_exec(["status", "--porcelain=v1", "-b"], cwd=validated_path)
    if code != 0:
        raise RuntimeError(f"Failed to inspect git status: {stderr.strip() or 'Unknown error'}")

    branch = "HEAD"
    staged: list[str] = []
    modified: list[str] = []
    untracked: list[str] = []
    deleted: list[str] = []

    lines = stdout.splitlines()
    for line in lines:
        if not line:
            continue
        if line.startswith("## "):
            # Branch header: ## branch_name...upstream [ahead 1]
            header = line[3:].strip()
            branch = header.split("...")[0].split()[0]
            continue

        if len(line) < 3:
            continue

        x = line[0]
        y = line[1]
        file_part = line[3:].strip()

        # Handle renamed files: "R  old -> new"
        if " -> " in file_part:
            file_part = file_part.split(" -> ")[-1].strip()

        # Skip ignored files
        if x == "!" and y == "!":
            continue

        # Untracked
        if x == "?" and y == "?":
            untracked.append(file_part)
            continue

        # Staged (X is non-space and not ?)
        if x in ("M", "A", "R", "D", "C"):
            staged.append(file_part)

        # Worktree modifications
        if y == "M":
            modified.append(file_part)
        elif y == "D":
            deleted.append(file_part)

    is_clean = not (staged or modified or untracked or deleted)

    return GitStatusResult(
        repo_path=str(validated_path),
        branch=branch,
        is_clean=is_clean,
        staged_files=staged,
        modified_files=modified,
        untracked_files=untracked,
        deleted_files=deleted,
    )
