"""Execution sandbox abstraction defining safety limits for test runners."""

from dataclasses import dataclass
from pathlib import Path

from app.core.config import Settings, get_settings
from app.developer.git.safety import validate_repo_path


@dataclass(frozen=True)
class ExecutionSandbox:
    """Defines isolated execution parameters and resource constraints for testing."""

    repo_path: Path
    timeout_seconds: float = 30.0
    max_output_bytes: int = 65536  # 64 KB limit

    @classmethod
    def create_for_repo(
        cls,
        repo_path: str,
        timeout_seconds: float = 30.0,
        settings: Settings | None = None,
    ) -> "ExecutionSandbox":
        """Create a validated execution sandbox for an approved repository."""
        cfg = settings or get_settings()
        validated = validate_repo_path(repo_path, cfg.get_approved_repo_roots())
        clamped_timeout = max(1.0, min(timeout_seconds, 120.0))
        return cls(repo_path=validated, timeout_seconds=clamped_timeout)
