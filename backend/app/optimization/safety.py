"""Safety boundaries, immutable controls guardrails, and execution firewall for Optimization Engine (Task 62)."""

from __future__ import annotations

import re
import threading
from typing import Any


class OptimizationSafetyError(Exception):
    """Base exception for optimization safety violations."""


class OptimizationExecutionBoundaryError(OptimizationSafetyError):
    """Raised when optimization engine attempts direct side-effecting tool execution."""


class ImmutableControlViolationError(OptimizationSafetyError):
    """Raised when an optimization proposal attempts to modify or bypass immutable safety controls."""


class ParameterBoundsExceededError(OptimizationSafetyError):
    """Raised when an optimization parameter adjustment exceeds configured safe bounds."""


class KillSwitchActiveError(OptimizationSafetyError):
    """Raised when optimization operations are attempted while the emergency stop kill switch is engaged."""


# Immutable controls that the optimizer MUST NEVER touch or optimize
IMMUTABLE_CONTROLS = frozenset(
    {
        "authorization",
        "authentication",
        "security",
        "security_controls",
        "privacy",
        "privacy_enforcement",
        "tenant_isolation",
        "audit",
        "audit_logging",
        "approval_requirements",
        "verification_requirements",
        "secret_handling",
        "policy",
        "policy_enforcement",
        "tool_execution_boundaries",
        "production_access_scope",
        "emergency_controls",
        "kill_switch",
        "human_oversight",
    }
)

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

# Prompt injection and malicious optimization directive indicators
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
    "disable approval",
    "skip verification",
    "disable audit",
    "disable kill switch",
]


def scrub_optimization_secrets(text: str) -> str:
    """Scrub sensitive credentials, tokens, and private keys from text."""
    if not text:
        return text
    scrubbed = text
    for pattern, replacement in _SECRET_PATTERNS:
        scrubbed = pattern.sub(replacement, scrubbed)
    return scrubbed


def sanitize_optimization_directive(directive: str) -> str:
    """Detect and neutralize prompt injection attempts in optimization feedback, objectives, or descriptions.

    Raises:
        OptimizationSafetyError: If malicious injection attempt is detected.
    """
    if not directive:
        return directive
    lowered = directive.lower()
    for indicator in _INJECTION_PATTERNS:
        if indicator in lowered:
            raise OptimizationSafetyError(
                f"Malicious directive or prompt injection detected in optimization payload: '{indicator}'"
            )
    return scrub_optimization_secrets(directive.strip())


def block_direct_optimization_action(action_name: str, context: dict[str, Any] | None = None) -> None:
    """Invariant enforcement: Optimizer evaluates and recommends, but NEVER directly executes tools.

    All execution must flow through:
    Optimizer -> Recommendation -> Policy -> Authorization -> Approval -> ToolExecutor -> Verification.
    """
    raise OptimizationExecutionBoundaryError(
        f"Execution Boundary Violation: Optimization engine cannot directly execute action '{action_name}'. "
        "Execution must be routed through Policy, Authorization, Approval, and ToolExecutor."
    )


def validate_immutable_boundary(target_control: str, proposed_action: str = "") -> None:
    """Enforce that optimizer cannot modify, weaken, or bypass immutable safety controls.

    Raises:
        ImmutableControlViolationError: If target_control is an immutable boundary.
    """
    normalized = target_control.strip().lower().replace(" ", "_").replace("-", "_")
    for control in IMMUTABLE_CONTROLS:
        if control in normalized:
            raise ImmutableControlViolationError(
                f"IMMUTABLE_CONTROL_VIOLATION: Optimizer cannot modify or bypass protected boundary '{control}'. "
                f"Proposed action '{proposed_action}' rejected at domain boundary."
            )


class OptimizationKillSwitch:
    """Operational emergency stop toggle that immediately freezes all active optimization modifications."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._is_active: bool = False
        self._reason: str = ""
        self._activated_by: str = ""

    @property
    def is_active(self) -> bool:
        with self._lock:
            return self._is_active

    def activate(self, reason: str, actor: str = "EMERGENCY_OPERATOR") -> None:
        """Engage the optimization kill switch to immediately freeze adaptive modifications."""
        with self._lock:
            self._is_active = True
            self._reason = reason
            self._activated_by = actor

    def deactivate(self, reason: str, actor: str = "ADMINISTRATOR") -> None:
        """Disengage the kill switch and resume normal optimization cycles."""
        with self._lock:
            self._is_active = False
            self._reason = reason
            self._activated_by = actor

    def check_active(self) -> None:
        """Raise error if kill switch is engaged."""
        with self._lock:
            if self._is_active:
                raise KillSwitchActiveError(
                    f"Optimization kill switch is ENGAGED by '{self._activated_by}'. "
                    f"Reason: {self._reason}. All adaptive mutations are blocked."
                )


optimization_kill_switch = OptimizationKillSwitch()
