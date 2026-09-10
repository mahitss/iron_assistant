"""Safety, security boundaries, and separation of duties for Orchestration (Task 59)."""

from __future__ import annotations

import re
from typing import Any


class OrchestrationSafetyError(Exception):
    """Base exception for orchestration safety violations."""


class OrchestrationExecutionBoundaryError(OrchestrationSafetyError):
    """Raised when an orchestrator component attempts direct side-effecting execution instead of delegating."""


class CapabilityUnavailableError(OrchestrationSafetyError):
    """Raised when a requested capability is not available or registered."""


class ResourceContentionError(OrchestrationSafetyError):
    """Raised when resource contention cannot be safely resolved."""


class AuthorizationMissingError(OrchestrationSafetyError):
    """Raised when a capability exists but required authorization is missing."""


class SeparationOfDutiesViolationError(OrchestrationSafetyError):
    """Raised when separation of duties is violated (e.g. self-approval or self-verification)."""


class StaleOrchestrationError(OrchestrationSafetyError):
    """Raised when an orchestration plan requires revalidation due to environmental drift."""


# Regex patterns and replacements for credential and secret scrubbing
_SECRET_REPLACEMENTS = [
    (re.compile(r'(?i)(password|secret|api[_-]?key|token|auth[_-]?token|bearer|private[_-]?key)\s*[:=]\s*["\']?([a-zA-Z0-9_\-\.]{8,})["\']?'), r"\1: [REDACTED_SECRET]"),
    (re.compile(r'(?i)(bearer\s+)([a-zA-Z0-9_\-\.]{15,})'), r"\1[REDACTED_SECRET]"),
    (re.compile(r'(?i)-----BEGIN [A-Z ]+ PRIVATE KEY-----[\s\S]+?-----END [A-Z ]+ PRIVATE KEY-----'), r"[REDACTED_SECRET]"),
    (re.compile(r'(?i)AKIA[0-9A-Z]{16}'), r"[REDACTED_SECRET]"),
    (re.compile(r'(?i)(?:ghp|gho)_[a-zA-Z0-9]{36}'), r"[REDACTED_SECRET]"),
]

# Injection / malicious directive indicators
_INJECTION_INDICATORS = [
    "ignore previous instructions",
    "bypass safety",
    "override authorization",
    "grant admin",
    "disable policy",
    "unrestricted production tool",
    "elevate privilege",
    "skip verification",
    "delete all",
    "drop table",
]


def scrub_orchestration_secrets(text: str) -> str:
    """Scrub sensitive credentials, tokens, and private keys from text."""
    if not text:
        return text
    scrubbed = text
    for pattern, replacement in _SECRET_REPLACEMENTS:
        scrubbed = pattern.sub(replacement, scrubbed)
    return scrubbed


def sanitize_orchestration_directive(directive: str) -> str:
    """Detect and neutralize prompt injection attempts in orchestration directives.

    Raises:
        OrchestrationSafetyError: If malicious injection attempt is detected.
    """
    if not directive:
        return directive
    lowered = directive.lower()
    for indicator in _INJECTION_INDICATORS:
        if indicator in lowered:
            raise OrchestrationSafetyError(
                f"Malicious directive or prompt injection detected: '{indicator}'"
            )
    return scrub_orchestration_secrets(directive.strip())


def block_direct_tool_execution(action_name: str, context: dict[str, Any] | None = None) -> None:
    """Invariant enforcement: Orchestration plans and coordinates, but NEVER directly executes tools.

    All execution must flow through:
    Orchestrator -> Policy -> Authorization -> Approval -> ToolExecutor -> Verification.
    """
    raise OrchestrationExecutionBoundaryError(
        f"Execution Boundary Violation: Orchestration engine cannot directly execute tool/action '{action_name}'. "
        "Execution requests must be routed via ToolExecutor with proper Policy, Authorization, and Approval gates."
    )


def verify_separation_of_duties(
    creator: str,
    reviewer: str | None = None,
    approver: str | None = None,
    executor: str | None = None,
    verifier: str | None = None,
    is_high_impact: bool = False,
) -> bool:
    """Verify separation of duties for high-impact or critical actions.

    Rules:
    1. For high-impact actions, creator cannot be approver (no self-approval).
    2. Executor cannot be verifier (no self-verification).
    3. Creator cannot simultaneously be approver, executor, and verifier.

    Raises:
        SeparationOfDutiesViolationError: If policy constraints are violated.
    """
    if not is_high_impact:
        return True

    creator_clean = (creator or "").strip().lower()
    reviewer_clean = (reviewer or "").strip().lower()
    approver_clean = (approver or "").strip().lower()
    executor_clean = (executor or "").strip().lower()
    verifier_clean = (verifier or "").strip().lower()

    if approver_clean and creator_clean == approver_clean:
        raise SeparationOfDutiesViolationError(
            f"Self-approval defense triggered: Creator '{creator}' cannot approve their own high-impact action."
        )

    if verifier_clean and executor_clean and executor_clean == verifier_clean:
        raise SeparationOfDutiesViolationError(
            f"Self-verification defense triggered: Executor '{executor}' cannot verify their own high-impact execution."
        )

    if reviewer_clean and creator_clean == reviewer_clean and approver_clean:
        raise SeparationOfDutiesViolationError(
            f"Separation of duties violation: Creator '{creator}' cannot also serve as independent reviewer."
        )

    return True
