"""Safety guards, invariant validators, and security exceptions for Environmental Intelligence (Task 54)."""

from __future__ import annotations

import re
from typing import Any


class EnvironmentSafetyError(Exception):
    """Base exception for environment safety violations."""


class SecretStorageViolationError(EnvironmentSafetyError):
    """Raised when an attempt is made to store raw secrets instead of references."""


class FalseTopologyError(EnvironmentSafetyError):
    """Raised when an unsubstantiated dependency or topology edge is asserted."""


class ProductionSafetyViolationError(EnvironmentSafetyError):
    """Raised when an unapproved or unsafe action is attempted against production."""


class UnauthorizedDiscoveryError(EnvironmentSafetyError):
    """Raised when discovery attempts to access resources outside authorized scope."""


class UnverifiedRollbackError(EnvironmentSafetyError):
    """Raised when rollback target has not been verified."""


class RemediationLoopError(EnvironmentSafetyError):
    """Raised when remediation loops or exceeds attempt budget."""


class FutureLeakageError(EnvironmentSafetyError):
    """Raised when a historical query attempts to use future state."""


SECRET_KEY_PATTERNS = [
    re.compile(r".*(password|passwd|pwd).*", re.IGNORECASE),
    re.compile(r".*(secret|api_key|apikey|token|auth_token|bearer|jwt).*", re.IGNORECASE),
    re.compile(r".*(private_key|priv_key|ssh_key|cert_key|cert).*", re.IGNORECASE),
    re.compile(r".*(credentials|access_key|secret_key).*", re.IGNORECASE),
]

SECRET_VALUE_PATTERNS = [
    re.compile(r"-----BEGIN (RSA|EC|DSA|OPENSSH|PGP) PRIVATE KEY-----"),
    re.compile(r"eyJ[a-zA-Z0-9_\-]+\.eyJ[a-zA-Z0-9_\-]+\.[a-zA-Z0-9_\-]+"),  # JWT
    re.compile(r"(ghp_[a-zA-Z0-9]{36}|github_pat_[a-zA-Z0-9]{82})"),  # GitHub tokens
    re.compile(r"AKIA[0-9A-Z]{16}"),  # AWS Access Key
]


class EnvironmentSafetyGuard:
    """Enforces digital twin invariants, secret protection, and production safeguards."""

    @staticmethod
    def inspect_and_sanitize_metadata(metadata: dict[str, Any], raise_on_secret: bool = True) -> dict[str, Any]:
        """Ensures no secret values are stored, redacting or raising as configured."""
        sanitized = {}
        for k, v in metadata.items():
            k_lower = str(k).lower()
            is_secret_key = any(pat.match(k_lower) for pat in SECRET_KEY_PATTERNS)
            if isinstance(v, str):
                is_secret_val = any(pat.search(v) for pat in SECRET_VALUE_PATTERNS)
            else:
                is_secret_val = False

            if is_secret_key or is_secret_val:
                is_reference = (
                    str(k_lower).endswith("_ref")
                    or str(k_lower).endswith("_id")
                    or str(k_lower).endswith("_arn")
                    or (isinstance(v, str) and (v.startswith("ref://") or v.startswith("vault://") or v.startswith("arn:")))
                )
                if not is_reference:
                    if raise_on_secret:
                        raise SecretStorageViolationError(
                            f"Detected potential secret value in metadata key '{k}'. Use secret references instead."
                        )
                    sanitized[k] = "[REDACTED_SECRET_REFERENCE]"
                else:
                    sanitized[k] = v
            elif isinstance(v, dict):
                sanitized[k] = EnvironmentSafetyGuard.inspect_and_sanitize_metadata(v, raise_on_secret=raise_on_secret)
            elif isinstance(v, list):
                sanitized[k] = [
                    EnvironmentSafetyGuard.inspect_and_sanitize_metadata(item, raise_on_secret=raise_on_secret)
                    if isinstance(item, dict)
                    else item
                    for item in v
                ]
            else:
                sanitized[k] = v
        return sanitized

    @staticmethod
    def validate_edge_topology(
        source_id: str,
        relationship: str,
        target_id: str,
        confidence: str,
        provenance: dict[str, Any],
        is_same_environment_only: bool = False,
    ) -> None:
        """Enforces prompt #10: Do not claim a dependency merely because two services exist in the same environment."""
        if source_id == target_id:
            raise FalseTopologyError("Self-referential dependency is not permitted as an external relationship.")

        if is_same_environment_only and confidence in ("VERIFIED", "OBSERVED"):
            raise FalseTopologyError(
                f"Cannot assert {confidence} relationship {relationship} between {source_id} and {target_id} "
                f"based solely on co-location in the same environment."
            )

        if not provenance or "source" not in provenance:
            if confidence in ("VERIFIED", "OBSERVED"):
                raise FalseTopologyError(
                    f"Relationship {relationship} between {source_id} and {target_id} requires verified provenance."
                )

    @staticmethod
    def validate_production_change(
        environment_type: str,
        action: str,
        is_approved: bool,
        has_verified_rollback: bool,
    ) -> None:
        """Enforces prompt #30, #109, #110, #117: Elevated scrutiny for production."""
        if environment_type.upper() in ("PRODUCTION", "PROD"):
            if not is_approved:
                raise ProductionSafetyViolationError(
                    f"Action '{action}' on PRODUCTION requires explicit approval."
                )
            if not has_verified_rollback:
                raise UnverifiedRollbackError(
                    f"Action '{action}' on PRODUCTION requires a verified rollback target."
                )
