"""Local Git inspection and safety module."""

from app.developer.git.diff import inspect_git_diff
from app.developer.git.history import inspect_git_branches, inspect_git_log
from app.developer.git.repository import LocalRepositoryRegistry, run_git_exec
from app.developer.git.safety import (
    PathSecurityError,
    redact_secrets,
    validate_file_path,
    validate_repo_path,
)
from app.developer.git.status import inspect_git_status

__all__ = [
    "LocalRepositoryRegistry",
    "PathSecurityError",
    "inspect_git_branches",
    "inspect_git_diff",
    "inspect_git_log",
    "inspect_git_status",
    "redact_secrets",
    "run_git_exec",
    "validate_file_path",
    "validate_repo_path",
]
