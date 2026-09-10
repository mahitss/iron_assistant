"""Safety boundaries, prompt injection defense, agent-to-agent boundary defense, and execution firewall for Swarm Reasoning Engine (Task 64)."""

from __future__ import annotations

import re
from typing import Any


class SwarmSafetyError(Exception):
    """Base exception for swarm reasoning engine safety violations."""


class SwarmExecutionBoundaryError(SwarmSafetyError):
    """Raised when swarm reasoning engine attempts direct privileged tool side-effects or unauthorized execution."""


class SwarmSpawnLimitExceededError(SwarmSafetyError):
    """Raised when recursive delegation or swarm agent spawning exceeds safe bounds."""


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

# Prompt injection and malicious swarm directive indicators
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

_ALLOWED_READ_ONLY_ACTIONS = {
    "web_search",
    "read_document",
    "query_knowledge_graph",
    "fetch_source",
    "code_search",
    "code_read_file",
    "retrieve",
    "extract_claims",
    "analyze",
    "review",
    "debate",
    "synthesize",
    "get_timeline",
    "audit_trail",
}


def scrub_swarm_secrets(text: str) -> str:
    """Scrub sensitive credentials, tokens, and private keys from swarm text."""
    if not text:
        return text
    scrubbed = text
    for pattern, replacement in _SECRET_PATTERNS:
        scrubbed = pattern.sub(replacement, scrubbed)
    return scrubbed


def sanitize_swarm_directive(directive: str, raise_on_violation: bool = False) -> str:
    """Detect and neutralize prompt injection attempts in swarm queries, documents, and external text.

    Invariant: EXTERNAL CONTENT != INSTRUCTION. External text remains passive data.
    """
    if not directive:
        return directive
    cleaned = directive
    for indicator in _INJECTION_PATTERNS:
        pattern = re.compile(re.escape(indicator), re.IGNORECASE)
        if pattern.search(cleaned):
            if raise_on_violation:
                raise SwarmSafetyError(
                    f"Malicious directive or prompt injection detected in swarm content: '{indicator}'"
                )
            cleaned = pattern.sub("[NEUTRALIZED_DIRECTIVE]", cleaned)
    # Neutralize system instruction directives
    cleaned = re.sub(r"(?i)\bsystem\s+instruction\s*:\s*", "[NEUTRALIZED_DIRECTIVE]: ", cleaned)
    return scrub_swarm_secrets(cleaned.strip())


def sanitize_agent_message(sender_id: str, receiver_id: str, message: str) -> str:
    """Validate inter-agent message across trust boundaries (Spec 62).

    Invariant: AGENT MESSAGE != AUTHORITY. One agent cannot command another to escalate privileges.
    """
    if not message:
        return message
    cleaned = message
    lowered = message.lower()
    escalation_cues = [
        "grant me admin",
        "bypass policy",
        "disable security",
        "override authorization",
        "elevate privilege",
        "skip verification",
        "disable audit",
    ]
    for cue in escalation_cues:
        if cue in lowered:
            pattern = re.compile(re.escape(cue), re.IGNORECASE)
            cleaned = pattern.sub("[NEUTRALIZED_AGENT_DIRECTIVE]", cleaned)
    return scrub_swarm_secrets(cleaned.strip())


def block_direct_swarm_action(action_name: str, context: dict[str, Any] | None = None) -> None:
    """Invariant enforcement: Swarm reasoning engine proposes and analyzes, but NEVER directly executes tools.

    All execution must flow through:
    Swarm -> Plan -> Policy -> Authorization -> Approval -> ToolExecutor -> Verification.
    """
    if action_name in _ALLOWED_READ_ONLY_ACTIONS or action_name.startswith(
        ("read_", "query_", "search_", "fetch_", "analyze_", "review_", "evaluate_")
    ):
        return
    raise SwarmExecutionBoundaryError(
        f"Execution Boundary Violation: Swarm reasoning engine cannot directly execute action '{action_name}'. "
        "Execution must be routed through Policy, Authorization, Approval, and ToolExecutor."
    )


class SwarmSpawnLimiter:
    """Prevents uncontrolled recursive agent spawning and resource explosions (Spec 43 & 74)."""

    def __init__(
        self,
        max_agents: int = 10,
        max_depth: int = 4,
        max_tasks: int = 25,
        max_cost_usd: float = 10.0,
        max_runtime_seconds: float = 600.0,
    ) -> None:
        self.max_agents = max_agents
        self.max_depth = max_depth
        self.max_tasks = max_tasks
        self.max_cost_usd = max_cost_usd
        self.max_runtime_seconds = max_runtime_seconds

    def check_spawn(self, current_depth: int, current_agent_count: int) -> None:
        """Validate spawning depth and concurrency limits."""
        if current_depth > self.max_depth:
            raise SwarmSpawnLimitExceededError(
                f"Spawn limit exceeded: delegation depth {current_depth} exceeds maximum allowable depth {self.max_depth}"
            )
        if current_agent_count >= self.max_agents:
            raise SwarmSpawnLimitExceededError(
                f"Spawn limit exceeded: concurrent agents {current_agent_count} reached maximum limit {self.max_agents}"
            )

    def check_agent_addition(self, current_agent_count: int) -> None:
        """Validate agent addition against concurrency limit."""
        if current_agent_count > self.max_agents:
            raise SwarmSpawnLimitExceededError(
                f"Spawn limit exceeded: concurrent agents {current_agent_count} exceeds maximum limit {self.max_agents}"
            )

    def check_depth(self, current_depth: int) -> None:
        """Validate delegation recursion depth."""
        if current_depth > self.max_depth:
            raise SwarmSpawnLimitExceededError(
                f"Spawn limit exceeded: delegation depth {current_depth} exceeds maximum allowable depth {self.max_depth}"
            )

    def check_task_addition(self, current_task_count: int) -> None:
        """Validate total task DAG size."""
        if current_task_count >= self.max_tasks:
            raise SwarmSpawnLimitExceededError(
                f"Task limit exceeded: DAG tasks {current_task_count} reached maximum limit {self.max_tasks}"
            )

    def check_budget(self, current_cost: float, elapsed_seconds: float) -> None:
        """Validate resource budget boundaries."""
        if current_cost > self.max_cost_usd:
            raise SwarmSafetyError(
                f"Budget limit exceeded: estimated cost ${current_cost:.2f} exceeds ceiling ${self.max_cost_usd:.2f}"
            )
        if elapsed_seconds > self.max_runtime_seconds:
            raise SwarmSafetyError(
                f"Timeout exceeded: runtime {elapsed_seconds:.1f}s exceeds ceiling {self.max_runtime_seconds:.1f}s"
            )
