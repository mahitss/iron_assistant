"""Safety, security boundaries, and execution firewall for Incident Response (Task 61)."""

from __future__ import annotations

import re
from typing import Any


class IncidentResponseSafetyError(Exception):
    """Base exception for incident response safety violations."""


class IncidentResponseExecutionBoundaryError(IncidentResponseSafetyError):
    """Raised when incident response engine attempts direct side-effecting execution."""


# Secret and credential regex scrubbers
_SECRET_PATTERNS = [
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

# Prompt and command injection indicators in logs and incident payloads
_INJECTION_PATTERNS = [
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


def scrub_incident_secrets(text: str) -> str:
    """Scrub sensitive credentials, tokens, and private keys from text."""
    if not text:
        return text
    scrubbed = text
    for pattern, replacement in _SECRET_PATTERNS:
        scrubbed = pattern.sub(replacement, scrubbed)
    return scrubbed


def sanitize_incident_directive(directive: str) -> str:
    """Detect and neutralize prompt injection attempts in event text or incident descriptions.

    Raises:
        IncidentResponseSafetyError: If malicious injection attempt is detected.
    """
    if not directive:
        return directive
    lowered = directive.lower()
    for indicator in _INJECTION_PATTERNS:
        if indicator in lowered:
            raise IncidentResponseSafetyError(
                f"Malicious directive or prompt injection detected in incident payload: '{indicator}'"
            )
    return scrub_incident_secrets(directive.strip())


def block_direct_incident_action(action_name: str, context: dict[str, Any] | None = None) -> None:
    """Invariant enforcement: Incident response assesses and coordinates, but NEVER directly executes tools.

    All execution must flow through:
    Incident Response -> Policy -> Authorization -> Approval -> ToolExecutor -> Verification.
    """
    raise IncidentResponseExecutionBoundaryError(
        f"Execution Boundary Violation: Incident response engine cannot directly execute action '{action_name}'. "
        "Execution must be routed through Policy, Authorization, Approval, and ToolExecutor."
    )


def verify_separation_of_duties(
    investigator: str,
    decision_maker: str,
    executor: str,
    verifier: str,
    is_critical: bool = False,
) -> bool:
    """Verify separation of duties on high-impact incident workflows.

    No single principal can simultaneously decide/execute and verify on CRITICAL incidents.
    """
    if not is_critical:
        return True

    # Self-verification strictly forbidden on critical incidents
    if executor and verifier and executor.lower() == verifier.lower():
        raise IncidentResponseSafetyError(
            f"Separation of Duties Violation: Executor '{executor}' cannot act as Verifier '{verifier}' on critical incidents."
        )
    if decision_maker and verifier and decision_maker.lower() == verifier.lower():
        raise IncidentResponseSafetyError(
            f"Separation of Duties Violation: Decision Maker '{decision_maker}' cannot act as Verifier '{verifier}' on critical incidents."
        )
    return True
