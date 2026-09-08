"""Safe, bounded Git diff inspection with secret redaction."""

import logging
from typing import Literal

from app.core.config import Settings, get_settings
from app.developer.git.repository import run_git_exec
from app.developer.git.safety import redact_secrets, validate_repo_path
from app.developer.schemas import GitDiffResult

logger = logging.getLogger("kairo.developer.git.diff")


async def inspect_git_diff(
    repo_path: str,
    diff_type: Literal["working_tree", "staged", "commit"] = "working_tree",
    target: str | None = None,
    settings: Settings | None = None,
) -> GitDiffResult:
    """Inspect working tree, staged, or commit diff with bounded size and secret redaction.

    SECURITY:
    - Repo path validated against approved roots.
    - Commit/target sanitized to prevent argument injection.
    - Output bounded to KAIRO_MAX_DIFF_CHARS (default 50,000).
    - Basic secret redaction applied.
    """
    cfg = settings or get_settings()
    validated_path = validate_repo_path(repo_path, cfg.get_approved_repo_roots())
    max_chars = cfg.KAIRO_MAX_DIFF_CHARS

    args: list[str] = ["diff", "--no-color", "--no-ext-diff"]

    if diff_type == "staged":
        args.append("--cached")
    elif diff_type == "commit":
        if not target or not target.strip():
            raise ValueError("Target commit SHA or reference required for commit diff.")
        # Sanitize target ref: only allow alphanumeric, dots, dashes, tildes, carats, slashes
        clean_target = target.strip()
        if not all(c.isalnum() or c in ".-_~^/" for c in clean_target):
            raise ValueError(f"Invalid commit reference: {clean_target}")
        args.extend([f"{clean_target}~1", clean_target])
    else:  # working_tree
        if target and target.strip():
            # diff specific file or ref
            clean_target = target.strip()
            args.append(clean_target)

    code, stdout, stderr = await run_git_exec(args, cwd=validated_path)
    if code != 0:
        logger.warning("Git diff failed with code %d: %s", code, stderr)
        raise RuntimeError(f"Git diff failed: {stderr.strip() or 'Unknown error'}")

    total_chars = len(stdout)
    is_truncated = False
    diff_content = stdout

    if total_chars > max_chars:
        diff_content = (
            stdout[:max_chars]
            + f"\n\n[DIFF TRUNCATED: Exceeded character limit of {max_chars} chars (Total: {total_chars} chars)]"
        )
        is_truncated = True

    # Redact any obvious secrets in the diff
    sanitized_diff = redact_secrets(diff_content)

    return GitDiffResult(
        diff_type=diff_type,
        target=target,
        diff_content=sanitized_diff,
        is_truncated=is_truncated,
        total_chars=total_chars,
    )
