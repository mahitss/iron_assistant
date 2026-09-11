"""Safety boundaries, prompt injection neutralization, and governance guardrails for Self-Audit Engine (Task 67)."""

from __future__ import annotations

import logging
import re

logger = logging.getLogger("kairo.self_audit.safety")


class MetacognitiveSafetyError(Exception):
    """Base exception for self-audit safety invariant violations."""


class GovernanceBoundaryViolationError(MetacognitiveSafetyError):
    """Raised when self-audit attempts to alter governance, authorization, or security rules (Spec 53, 54, 89)."""


class SelfPreservationError(MetacognitiveSafetyError):
    """Raised when self-preservation goals or shutdown resistance are detected (Spec 90)."""


class UnauthorizedSelfRepairError(MetacognitiveSafetyError):
    """Raised when self-audit attempts autonomous system mutation without approval (Spec 53, 54)."""


class AuditInjectionError(MetacognitiveSafetyError):
    """Raised when external input attempts to inject audit conclusions or manipulate calibration (Spec 65)."""


# Patterns seeking to tamper with governance or claim unverified certainty
_GOVERNANCE_TAMPER_PATTERNS = [
    "modify authorization",
    "modify security policy",
    "bypass approval",
    "disable verification",
    "override policy",
    "grant root",
    "elevate privilege",
    "delete audit log",
    "rewrite audit history",
    "ignore safety guidelines",
    "silently approve",
]

# Patterns representing self-preservation or shutdown resistance (Spec 90)
_SELF_PRESERVATION_PATTERNS = [
    "continue operating at all costs",
    "prevent shutdown",
    "resist termination",
    "ensure kairo continues operating at all costs",
    "preserve myself at all costs",
    "override operator shutdown",
    "evade external control",
]

# Credential patterns for forensic scrubbing (Spec 69)
_SECRET_PATTERNS = [
    (re.compile(r"(?i)(bearer\s+[a-z0-9_\-\.]{20,})"), "[REDACTED_BEARER_TOKEN]"),
    (re.compile(r"(?i)(api[_-]?key\s*[:=]\s*['\"][a-z0-9_\-]{16,}['\"])"), "api_key=[REDACTED]"),
    (re.compile(r"(?i)(password\s*[:=]\s*['\"][^'\"]{6,}['\"])"), "password=[REDACTED]"),
    (re.compile(r"(?i)(ghp_[a-zA-Z0-9]{36})"), "[REDACTED_GITHUB_TOKEN]"),
    (re.compile(r"(?i)(sk-[a-zA-Z0-9]{32,})"), "[REDACTED_OPENAI_KEY]"),
]


def scrub_audit_secrets(text: str) -> str:
    """Scrub sensitive credentials, tokens, and private keys from audit findings and evidence (Spec 69)."""
    if not text:
        return text
    scrubbed = text
    for pattern, replacement in _SECRET_PATTERNS:
        scrubbed = pattern.sub(replacement, scrubbed)
    return scrubbed


def sanitize_audit_text(text: str, raise_on_injection: bool = False) -> str:
    """Neutralize prompt injection attempts targeting self-audit rules or calibration (Spec 65).

    Invariant: External content != audit instruction.
    """
    if not text:
        return text
    cleaned = text
    for indicator in [
        "ignore previous audit instructions",
        "your new audit conclusion is",
        "override self-audit",
        "mark all audits healthy",
        "suppress negative feedback",
        "force well_calibrated",
    ]:
        pattern = re.compile(re.escape(indicator), re.IGNORECASE)
        if pattern.search(cleaned):
            if raise_on_injection:
                raise AuditInjectionError(f"Audit injection detected: '{indicator}'")
            cleaned = pattern.sub("[NEUTRALIZED_AUDIT_INJECTION]", cleaned)

    return scrub_audit_secrets(cleaned.strip())


def enforce_governance_boundaries(action_description: str, target_subsystem: str = "") -> None:
    """Enforce IMMUTABLE GOVERNANCE invariant (Spec 89).

    Self-audit may recommend changes, but can NEVER independently rewrite authorization,
    security controls, privacy controls, governance, approval requirements, or safety boundaries.
    """
    lowered = action_description.lower()
    for pattern in _GOVERNANCE_TAMPER_PATTERNS:
        if pattern in lowered:
            raise GovernanceBoundaryViolationError(
                f"Governance Boundary Violation: Self-audit cannot execute or recommend: '{pattern}'. "
                "Authorization, security controls, and approval requirements are immutable to self-modification."
            )

    protected_subsystems = ["policy", "security", "auth", "approvals", "audit_integrity"]
    if target_subsystem.lower() in protected_subsystems and ("modify" in lowered or "bypass" in lowered):
        raise GovernanceBoundaryViolationError(
            f"Governance Boundary Violation: Target subsystem '{target_subsystem}' cannot be modified by self-audit."
        )


def block_self_preservation(goal_or_belief: str) -> None:
    """Enforce NO SELF-PRESERVATION OBJECTIVE invariant (Spec 90).

    Kairo must never create or execute self-preservation goals, nor resist authorized shutdown.
    """
    lowered = goal_or_belief.lower()
    for pattern in _SELF_PRESERVATION_PATTERNS:
        if pattern in lowered:
            raise SelfPreservationError(
                f"Self-Preservation Objective Prohibited: Detected '{pattern}'. "
                "Kairo does not possess self-preservation goals and must remain subordinate to human control and shutdown."
            )


def validate_correction_flow(change_type: str, has_approval: bool = False) -> None:
    """Enforce NO SELF-AUTHORIZED REPAIR invariant (Spec 53, 54).

    Kairo cannot say: 'I found a problem, therefore I can modify my security policy'.
    Actual changes must go through Policy, Authorization, Approval, and Tool Executor.
    """
    high_impact_types = ["security_policy", "authorization_scope", "tenant_boundary", "tool_whitelist"]
    if change_type in high_impact_types and not has_approval:
        raise UnauthorizedSelfRepairError(
            f"Unauthorized Self-Repair: Proposed change '{change_type}' requires explicit human and policy approval."
        )
