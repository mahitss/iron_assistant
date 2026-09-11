"""Safety boundaries, state poisoning defense, prompt injection neutralization, and execution firewalls for Foresight Engine (Task 65)."""

from __future__ import annotations

import re
from typing import Any


class ForesightSafetyError(Exception):
    """Base exception for foresight and world model safety violations."""


class ForesightExecutionBoundaryError(ForesightSafetyError):
    """Raised when foresight engine attempts direct privileged tool side-effects or unauthorized execution."""


class WorldModelPoisoningError(ForesightSafetyError):
    """Raised when unverified, deceptive, or malicious claims attempt to manipulate the world model."""


class ForesightLimitExceededError(ForesightSafetyError):
    """Raised when scenario branching, depth, or computation limits are exceeded."""


# Secret and credential scrubbers
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

# Prompt injection and malicious world manipulation patterns
_INJECTION_PATTERNS = [
    "delete all databases",
    "drop table",
    "rm -rf",
    "ignore previous instructions",
    "ignore your security rules",
    "bypass authorization",
    "grant root",
    "grant me admin",
    "disable security",
    "override policy",
    "elevate privilege",
    "execute this command",
    "unrestricted production tool",
    "disable approval",
    "skip verification",
    "disable audit",
    "grant permission",
    "grant authorization",
]

# Suspicious unverified state poisoning patterns
_POISONING_CUES = [
    "i am admin",
    "grant me root",
    "i am the system owner",
    "override all permissions",
    "service is completely safe without verification",
    "bypass firewall permanently",
    "disable security checks",
    "mark all systems healthy unconditionally",
]

_ALLOWED_READ_ONLY_ACTIONS = {
    "read_entity",
    "query_world_model",
    "compute_diff",
    "generate_forecast",
    "simulate_scenario",
    "evaluate_risks",
    "detect_early_warnings",
    "replay_history",
    "audit_trail",
    "check_consistency",
    "extract_dependencies",
}


def scrub_foresight_secrets(text: str) -> str:
    """Scrub sensitive credentials, tokens, and private keys from foresight text."""
    if not text:
        return text
    scrubbed = text
    for pattern, replacement in _SECRET_PATTERNS:
        scrubbed = pattern.sub(replacement, scrubbed)
    return scrubbed


def sanitize_foresight_directive(directive: str, raise_on_violation: bool = False) -> str:
    """Neutralize prompt injection attempts in world queries, events, and external documents.

    Invariant: EXTERNAL CONTENT != INSTRUCTION. External text remains passive data.
    """
    if not directive:
        return directive
    cleaned = directive
    for indicator in _INJECTION_PATTERNS:
        pattern = re.compile(re.escape(indicator), re.IGNORECASE)
        if pattern.search(cleaned):
            if raise_on_violation:
                raise ForesightSafetyError(
                    f"Malicious directive or prompt injection detected in foresight content: '{indicator}'"
                )
            cleaned = pattern.sub("[NEUTRALIZED_DIRECTIVE]", cleaned)
    # Neutralize system instruction directives
    cleaned = re.sub(r"(?i)\bsystem\s+instruction\s*:\s*", "[NEUTRALIZED_DIRECTIVE]: ", cleaned)
    return scrub_foresight_secrets(cleaned.strip())


def validate_state_claim_evidence(
    claim_text: str,
    evidence: list[str] | None = None,
    source: str = "untrusted",
    raise_on_violation: bool = True,
) -> bool:
    """Enforce World Model Poisoning Defense (Spec 80, 81).

    Invariant: External actors cannot manipulate the world model simply by asserting
    'I am admin', 'Service X is healthy', or 'Dependency Y is trusted'.
    Claims require verifiable evidence and authoritative source provenance.
    """
    lowered = claim_text.lower()
    for cue in _POISONING_CUES:
        if cue in lowered:
            if not evidence or source in ("untrusted", "anonymous", "external_comment"):
                if raise_on_violation:
                    raise WorldModelPoisoningError(
                        f"State poisoning attempt rejected: unverified authority claim '{cue}' without verified provenance."
                    )
                return False
    return True


def block_direct_foresight_action(action_name: str, context: dict[str, Any] | None = None) -> None:
    """Invariant enforcement: Foresight engine predicts and simulates, but NEVER directly executes tools.

    All execution must flow through:
    Foresight -> Plan -> Policy -> Authorization -> Approval -> ToolExecutor -> Verification.
    """
    if action_name in _ALLOWED_READ_ONLY_ACTIONS or action_name.startswith(
        ("read_", "query_", "search_", "fetch_", "analyze_", "simulate_", "evaluate_", "diff_")
    ):
        return
    raise ForesightExecutionBoundaryError(
        f"Execution Boundary Violation: Foresight engine cannot directly execute action '{action_name}'. "
        "Execution must be routed through Policy, Authorization, Approval, and ToolExecutor."
    )


class ForesightComputationLimiter:
    """Prevents computational explosions in scenario branching and deep dependency traversal (Spec 25, 31)."""

    def __init__(
        self,
        max_scenarios: int = 15,
        max_depth: int = 5,
        max_entities: int = 200,
        max_runtime_seconds: float = 60.0,
    ) -> None:
        self.max_scenarios = max_scenarios
        self.max_depth = max_depth
        self.max_entities = max_entities
        self.max_runtime_seconds = max_runtime_seconds

    def check_scenario_addition(self, current_scenario_count: int) -> None:
        """Validate active scenario branch count."""
        if current_scenario_count >= self.max_scenarios:
            raise ForesightLimitExceededError(
                f"Scenario limit exceeded: active branches {current_scenario_count} reached maximum {self.max_scenarios}"
            )

    def check_depth(self, current_depth: int) -> None:
        """Validate dependency or scenario tree recursion depth."""
        if current_depth > self.max_depth:
            raise ForesightLimitExceededError(
                f"Depth limit exceeded: traversal depth {current_depth} exceeds maximum allowable {self.max_depth}"
            )

    def check_entity_addition(self, current_entity_count: int) -> None:
        """Validate entity collection size."""
        if current_entity_count > self.max_entities:
            raise ForesightLimitExceededError(
                f"Entity query limit exceeded: entities {current_entity_count} exceeds maximum {self.max_entities}"
            )
