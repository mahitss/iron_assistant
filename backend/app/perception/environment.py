"""Environment Types, Cross-Environment Isolation, and Boundary Guards (Task 46)."""

from __future__ import annotations

from enum import Enum
import logging
from typing import Optional

logger = logging.getLogger("kairo.perception.environment")


class EnvironmentType(str, Enum):
    """6 isolated operational environments (Spec 77)."""

    LOCAL = "LOCAL"
    DEVELOPMENT = "DEVELOPMENT"
    STAGING = "STAGING"
    PRODUCTION = "PRODUCTION"
    TEST = "TEST"
    SANDBOX = "SANDBOX"


class EnvironmentIsolationError(Exception):
    """Raised when an operation attempts to mix or contaminate state across isolated environments (Spec 78)."""


class EnvironmentBoundaryGuard:
    """Enforces strict isolation between environments (e.g., prod observations never mutate dev state) (Spec 78)."""

    @classmethod
    def validate_environment_boundary(
        cls,
        observation_env: str,
        target_env: str,
    ) -> None:
        """Verify that telemetry from one environment does not bleed into another (Spec 78)."""
        src = observation_env.upper().strip()
        tgt = target_env.upper().strip()

        if src != tgt:
            logger.critical(
                "CROSS-ENVIRONMENT VIOLATION: Ingestion from '%s' attempted to update state of '%s'",
                src,
                tgt,
            )
            raise EnvironmentIsolationError(
                f"Cross-environment contamination blocked: Cannot apply {src} observation to {tgt} state."
            )

    validate_environment_access = validate_environment_boundary

