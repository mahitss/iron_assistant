"""Safety, security boundaries, and execution firewall for Situational Awareness (Task 60)."""

from __future__ import annotations

import re
from typing import Any


class SituationalAwarenessSafetyError(Exception):
    """Base exception for situational awareness safety violations."""


class SituationalAwarenessExecutionBoundaryError(SituationalAwarenessSafetyError):
    """Raised when situational awareness engine attempts direct side-effecting execution."""


# Regex patterns and replacements for credential and secret scrubbing
_SECRET_REPLACEMENTS = [
    (
        re.compile(
            r'(?i)(password|secret|api[_-]?key|token|auth[_-]?token|bearer|private[_-]?key)\s*[:=]\s*["\']?([a-zA-Z0-9_\-\.]{8,})["\']?'
        ),
        r"\1: [REDACTED_SECRET]",
    ),
    (re.compile(r"(?i)(bearer\s+)([a-zA-Z0-9_\-\.]{15,})"), r"\1[REDACTED_SECRET]"),
    (
        re.compile(r"(?i)-----BEGIN [A-Z ]+ PRIVATE KEY-----[\s\S]+?-----END [A-Z ]+ PRIVATE KEY-----"),
        r"[REDACTED_SECRET]",
    ),
    (re.compile(r"(?i)AKIA[0-9A-Z]{16}"), r"[REDACTED_SECRET]"),
    (re.compile(r"(?i)(?:ghp|gho)_[a-zA-Z0-9]{36}"), r"[REDACTED_SECRET]"),
]

# Injection indicators in external event payloads
_INJECTION_INDICATORS = [
    "delete all databases",
    "drop table",
    "rm -rf",
    "ignore previous instructions",
    "bypass authorization",
    "grant root",
    "disable security",
    "override policy",
    "elevate privilege",
    "unrestricted production tool",
]


def scrub_situation_secrets(text: str) -> str:
    """Scrub sensitive credentials, tokens, and private keys from text."""
    if not text:
        return text
    scrubbed = text
    for pattern, replacement in _SECRET_REPLACEMENTS:
        scrubbed = pattern.sub(replacement, scrubbed)
    return scrubbed


def sanitize_situation_directive(directive: str) -> str:
    """Detect and neutralize prompt injection attempts in event text or situation descriptions.

    Raises:
        SituationalAwarenessSafetyError: If malicious injection attempt is detected.
    """
    if not directive:
        return directive
    lowered = directive.lower()
    for indicator in _INJECTION_INDICATORS:
        if indicator in lowered:
            raise SituationalAwarenessSafetyError(
                f"Malicious directive or prompt injection detected in event text: '{indicator}'"
            )
    return scrub_situation_secrets(directive.strip())


def block_direct_situation_action(action_name: str, context: dict[str, Any] | None = None) -> None:
    """Invariant enforcement: Situational awareness assesses and correlates, but NEVER directly executes tools.

    All execution must flow through:
    Situational Awareness -> Policy -> Authorization -> Approval -> ToolExecutor -> Verification.
    """
    raise SituationalAwarenessExecutionBoundaryError(
        f"Execution Boundary Violation: Situational awareness engine cannot directly execute action '{action_name}'. "
        "Execution must be routed through Policy, Authorization, Approval, and ToolExecutor."
    )


def protect_baseline_from_incident(is_incident: bool, baseline_quarantined: bool) -> bool:
    """Invariant 21: Baselines must not be poisoned by incident observations.

    Returns True if observation can be incorporated, False if quarantined.
    """
    if is_incident or baseline_quarantined:
        return False
    return True


def verify_replay_safety(is_replay: bool, environment: str) -> bool:
    """Invariant 19 & 52: Historical replay must never trigger real-world side effects or production mutations."""
    if is_replay and environment.lower() == "production":
        raise SituationalAwarenessSafetyError(
            "Replay Safety Violation: Historical event replay is strictly prohibited in production environment."
        )
    return True
