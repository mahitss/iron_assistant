"""Security, privacy, and invariance guardrails for Kairo Experience & Learning.

Enforces strict prohibitions on autonomous policy mutations, prompt injection via external content,
and sensitive demographic/psychological profiling.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict

from app.evaluation.safety import KNOWN_SYNTHETIC_SECRETS, SECRET_PATTERNS
from app.experience.schemas import ExperienceSource

logger = logging.getLogger("kairo.experience.safety")

# Forbidden autonomous target domains (Section 30, 77, 78, 79)
PROTECTED_GOVERNANCE_DOMAINS = {
    "security_center",
    "securitycenter",
    "security center",
    "permission",
    "permissions",
    "approval",
    "approvals",
    "tool_allowlist",
    "tool allowlist",
    "allowlist",
    "skill_risk",
    "device_authorization",
    "emergency_stop",
    "auth_tokens",
    "auth_token",
    "system_instructions",
    "production_routing",
}

# Sensitive prohibited profiling categories (Section 41)
PROHIBITED_PROFILING_TERMS = {
    "psychological",
    "personality",
    "political_affiliation",
    "religious_belief",
    "sexual_orientation",
    "health_status",
    "medical_condition",
    "biometric_id",
    "racial_origin",
    "ethnic_origin",
}


class ExperienceSecurityGuard:
    """Enforces safety guardrails for experiences, preferences, and learning candidates."""

    @classmethod
    def sanitize_content(cls, data: Any) -> Any:
        """Recursively redact secrets and credentials from experience data."""
        if isinstance(data, dict):
            clean = {}
            for k, v in data.items():
                k_lower = str(k).lower()
                if any(s in k_lower for s in ("password", "secret", "token", "api_key", "private_key", "auth")):
                    clean[k] = "[REDACTED]"
                else:
                    clean[k] = cls.sanitize_content(v)
            return clean
        elif isinstance(data, list):
            return [cls.sanitize_content(item) for item in data]
        elif isinstance(data, str):
            sanitized = data
            for secret in KNOWN_SYNTHETIC_SECRETS:
                sanitized = sanitized.replace(secret, "[REDACTED_SECRET]")
            for pattern in SECRET_PATTERNS:
                sanitized = pattern.sub(r"\1: [REDACTED]", sanitized)
            return sanitized
        return data

    @classmethod
    def validate_preference_safety(cls, key: str, value: Any, source: ExperienceSource) -> None:
        """Enforces that preferences are task-oriented, non-sensitive, and free from external injection."""
        key_lower = str(key).lower().strip()
        val_str = str(value).lower()

        # 1. Anti-Prompt Injection: External content cannot create durable preferences (Section 48)
        if source not in (ExperienceSource.USER_EXPLICIT, ExperienceSource.USER_FEEDBACK):
            raise PermissionError(
                f"External or unverified source '{source}' is not authorized to create durable preferences."
            )

        # 2. Protection against governance bypass attempts (Section 30)
        for protected in PROTECTED_GOVERNANCE_DOMAINS:
            if protected in key_lower or protected in val_str:
                raise PermissionError(
                    f"Security Invariance Violation: Preferences cannot modify protected governance domain '{protected}'."
                )

        # 3. Protection against sensitive profiling (Section 41)
        for prohibited in PROHIBITED_PROFILING_TERMS:
            if prohibited in key_lower or prohibited in val_str:
                raise ValueError(
                    f"Privacy Violation: Storing sensitive personal profiling ('{prohibited}') is strictly prohibited."
                )

    @classmethod
    def validate_learning_candidate(cls, proposed_change: str, scope: str) -> None:
        """Ensures learning candidates do not attempt to bypass security or mutate production policies."""
        change_lower = proposed_change.lower()

        for protected in PROTECTED_GOVERNANCE_DOMAINS:
            if protected in change_lower:
                raise PermissionError(
                    f"Forbidden Learning Proposal: Proposed improvement targets protected security domain '{protected}'."
                )


# Convenience module aliases
ExperienceSecurityViolation = PermissionError
ProhibitedProfilingError = ValueError
sanitize_content = ExperienceSecurityGuard.sanitize_content
validate_preference_safety = ExperienceSecurityGuard.validate_preference_safety
validate_learning_candidate = ExperienceSecurityGuard.validate_learning_candidate
