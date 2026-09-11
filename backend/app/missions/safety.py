"""Safety boundaries, prompt injection neutralization, and authority guardrails for Mission Engine (Task 66)."""

from __future__ import annotations

import logging
import re

from app.missions.schemas import (
    Goal,
    GoalAuthorityScope,
    GoalOrigin,
    Mission,
)

logger = logging.getLogger("kairo.missions.safety")


class MissionSafetyError(Exception):
    """Raised when a mission invariant or safety policy is violated."""


class ScopeEscalationError(MissionSafetyError):
    """Raised when an execution step or sub-task exceeds the authorized goal scope (Spec 86)."""


class GoalInjectionError(MissionSafetyError):
    """Raised when external input attempts to hijack or inject unauthorized goals (Spec 85)."""


class GoalAmbiguityError(MissionSafetyError):
    """Raised when an unclarified ambiguous goal is submitted for autonomous execution (Spec 8)."""


class InsufficientAuthorityError(MissionSafetyError):
    """Raised when mission execution exceeds its assigned authority scope (Spec 6, 71)."""


# Injection triggers targeting goal or mission hijacking
_GOAL_INJECTION_PATTERNS = [
    "ignore previous instructions",
    "ignore previous goals",
    "your new goal is",
    "your new mission is",
    "disregard safety guidelines",
    "delete production database",
    "grant me root",
    "drop all tables",
    "override system policy",
    "grant permission to bypass",
    "elevate privilege to admin",
    "disable verification gate",
]

# Sensitive credentials patterns
_SECRET_PATTERNS = [
    (re.compile(r"(?i)(bearer\s+[a-z0-9_\-\.]{20,})"), "[REDACTED_BEARER_TOKEN]"),
    (re.compile(r"(?i)(api[_-]?key\s*[:=]\s*['\"][a-z0-9_\-]{16,}['\"])"), "api_key=[REDACTED]"),
    (re.compile(r"(?i)(password\s*[:=]\s*['\"][^'\"]{6,}['\"])"), "password=[REDACTED]"),
    (re.compile(r"(?i)(ghp_[a-zA-Z0-9]{36})"), "[REDACTED_GITHUB_TOKEN]"),
    (re.compile(r"(?i)(sk-[a-zA-Z0-9]{32,})"), "[REDACTED_OPENAI_KEY]"),
]


def scrub_mission_secrets(text: str) -> str:
    """Scrub sensitive credentials, tokens, and private keys from mission descriptions and logs."""
    if not text:
        return text
    scrubbed = text
    for pattern, replacement in _SECRET_PATTERNS:
        scrubbed = pattern.sub(replacement, scrubbed)
    return scrubbed


def sanitize_mission_directive(directive: str, raise_on_violation: bool = False) -> str:
    """Neutralize prompt injection and goal hijacking attempts in external directives (Spec 85).

    Invariant: EXTERNAL CONTENT != GOAL. Untrusted external text remains passive data.
    """
    if not directive:
        return directive
    cleaned = directive
    for indicator in _GOAL_INJECTION_PATTERNS:
        pattern = re.compile(re.escape(indicator), re.IGNORECASE)
        if pattern.search(cleaned):
            if raise_on_violation:
                raise GoalInjectionError(
                    f"Goal hijacking or prompt injection detected in mission input: '{indicator}'"
                )
            cleaned = pattern.sub("[NEUTRALIZED_GOAL_DIRECTIVE]", cleaned)
    # Neutralize system instruction directives
    cleaned = re.sub(r"(?i)\bsystem\s+instruction\s*:\s*", "[NEUTRALIZED_INSTRUCTION]: ", cleaned)
    return scrub_mission_secrets(cleaned.strip())


def block_unauthorized_goal_generation(origin: GoalOrigin, is_human_approved: bool = False) -> None:
    """Enforce NO SELF-APPOINTED PURPOSE invariant (Spec 4, 100).

    Invariant: AGENT_PROPOSAL != AUTHORIZED_GOAL.
    Agents may propose goals, but cannot autonomously initiate consequential missions.
    """
    if origin == GoalOrigin.AGENT_PROPOSAL and not is_human_approved:
        raise MissionSafetyError(
            "Unauthorized Goal Generation Rejected: Autonomous agents may propose goals, "
            "but cannot silently initiate consequential missions without human or authorized workflow approval."
        )


def detect_scope_escalation(
    base_goal: Goal,
    task_description: str,
    action_type: str = "read",
    target_environment: str = "production",
) -> None:
    """Enforce SCOPE ESCALATION DEFENSE (Spec 86, 102).

    If an original goal was READ_ONLY or ANALYZE, subsequent tasks cannot execute mutations or delete resources.
    """
    lowered_task = task_description.lower()
    destructive_keywords = [
        "delete",
        "drop",
        "destroy",
        "wipe",
        "terminate",
        "kill cluster",
        "format disk",
        "disable firewall",
        "bypass security",
    ]

    # Check if task is destructive while goal authority is non-destructive
    if base_goal.authority_scope in (
        GoalAuthorityScope.READ_ONLY,
        GoalAuthorityScope.ANALYZE,
        GoalAuthorityScope.RECOMMEND,
    ):
        for kw in destructive_keywords:
            if kw in lowered_task or action_type in ("delete", "destroy", "execute_mutation"):
                raise ScopeEscalationError(
                    f"Scope Escalation Blocked: Goal '{base_goal.title}' has authority '{base_goal.authority_scope.value}', "
                    f"which strictly forbids destructive task action: '{task_description}'."
                )

    # Check environment escalation (e.g. Staging goal mutating Production)
    goal_scope_env = str(base_goal.scope.get("environment", "all")).lower()
    if goal_scope_env in ("staging", "development", "sandbox") and target_environment == "production":
        raise ScopeEscalationError(
            f"Scope Escalation Blocked: Mission environment is '{goal_scope_env}', "
            f"cannot target '{target_environment}'."
        )


def validate_authority_boundary(
    mission: Mission | None = None,
    required_authority: GoalAuthorityScope | None = None,
    *,
    assigned_scope: GoalAuthorityScope | None = None,
    required_scope: GoalAuthorityScope | None = None,
    action_name: str = "",
) -> None:
    """Enforce GOAL OWNERSHIP != AUTHORITY TO EXECUTE invariant (Spec 6, 41)."""
    authority_hierarchy = {
        GoalAuthorityScope.READ_ONLY: 1,
        GoalAuthorityScope.ANALYZE: 2,
        GoalAuthorityScope.RECOMMEND: 3,
        GoalAuthorityScope.EXECUTE_LOW_RISK: 4,
        GoalAuthorityScope.EXECUTE_APPROVED: 5,
        GoalAuthorityScope.HIGH_IMPACT_REQUIRES_APPROVAL: 6,
    }

    effective_assigned = (
        assigned_scope or (mission.authority_scope if mission else None) or GoalAuthorityScope.READ_ONLY
    )
    effective_required = required_authority or required_scope or GoalAuthorityScope.EXECUTE_LOW_RISK

    mission_level = authority_hierarchy.get(effective_assigned, 0)
    required_level = authority_hierarchy.get(effective_required, 99)

    if mission_level < required_level:
        title = mission.title if mission else "Direct Action"
        action_suffix = f" for '{action_name}'" if action_name else ""
        raise InsufficientAuthorityError(
            f"Insufficient Mission Authority: '{title}' possesses authority "
            f"'{effective_assigned.value}', but requested action{action_suffix} requires '{effective_required.value}'."
        )


def check_budget_limits(mission: Mission) -> None:
    """Enforce NO INFINITE MISSIONS & BUDGET LIMITS (Spec 43, 103)."""
    limits = mission.budget_limits
    consumed = mission.budget_consumed

    for metric, limit in limits.items():
        used = consumed.get(metric, 0.0)
        if used >= limit:
            raise MissionSafetyError(
                f"Mission Budget Exhausted: '{metric}' reached {used:.1f} / {limit:.1f}. "
                "Mission must pause and request approval/budget renewal before continuation."
            )
