"""Central policies, risk assessment, anti-drift, anti-injection, and autonomy rules (Spec 17-21, 59-61, 137-141, 149-154)."""

import logging
import re
from datetime import UTC, datetime, timedelta
from typing import Any, Tuple

from app.security.risk import RiskLevel
from app.tasks.schemas import (
    AutonomyLevel,
    TaskRiskLevel,
    TaskStepSchema,
)

logger = logging.getLogger("kairo.tasks.policies")

# Destructive action keywords and patterns that ALWAYS require explicit approval
DESTRUCTIVE_PATTERNS = [
    r"\b(delete|drop|purge|destroy|truncate|wipe|erase|unlink)\b",
    r"\b(rm\s+-rf|del\s+/f|format\s+[a-z]:)\b",
    r"\b(grant\s+all|chmod\s+777|disable\s+firewall|disable\s+security)\b",
    r"\b(push\s+--force|reset\s+--hard)\b",
    r"\b(kill\s+-9|terminate\s+instance)\b",
]

# High-risk target keywords
HIGH_RISK_TARGETS = ["production", "prod", "main", "master", "database", "security", "credentials", "secrets"]


class TaskPolicyViolationError(PermissionError):
    """Raised when an autonomous step violates task policy boundaries."""
    pass


class TaskPolicyEngine:
    """Authoritative evaluator of task-level and step-level execution policies."""

    @classmethod
    def classify_step_risk(
        cls,
        title: str,
        objective: str,
        tool_name: str | None = None,
        skill_id: str | None = None,
        arguments: dict[str, Any] | None = None,
    ) -> TaskRiskLevel:
        """Classify step risk into READ, WRITE, or DESTRUCTIVE based on actions and targets."""
        combined_text = f"{title} {objective} {tool_name or ''} {skill_id or ''}".lower()
        if arguments:
            combined_text += f" {str(arguments).lower()}"

        # 1. Check for destructive patterns
        for pat in DESTRUCTIVE_PATTERNS:
            if re.search(pat, combined_text):
                return TaskRiskLevel.DESTRUCTIVE

        # 2. Check for mutation / write patterns
        write_indicators = [
            "write", "modify", "update", "patch", "edit", "create", "insert",
            "commit", "push", "apply", "install", "deploy", "save", "post"
        ]
        for w in write_indicators:
            if re.search(rf"\b{w}\b", combined_text):
                return TaskRiskLevel.WRITE

        return TaskRiskLevel.READ

    @classmethod
    def requires_approval(
        cls,
        step: TaskStepSchema,
        autonomy_level: AutonomyLevel = AutonomyLevel.SUPERVISED,
        project_policy: str | None = None,
    ) -> Tuple[bool, str]:
        """Determine if a step requires human approval before dispatch.

        Rules:
        - ASSISTED: All steps require confirmation.
        - DESTRUCTIVE: ALWAYS requires explicit approval across ALL autonomy levels.
        - SUPERVISED (Default): READ steps execute autonomously; WRITE steps require approval.
        - AUTONOMOUS_READ: READ steps execute autonomously; WRITE steps are BLOCKED or require approval.
        - AUTONOMOUS_BOUNDED: Low/medium writes allowed if bounded; destructive still requires approval.
        - Production projects downgrade autonomy to require approvals on any modification.
        """
        # 1. Hard invariant: Destructive actions ALWAYS require approval
        if step.risk_level == TaskRiskLevel.DESTRUCTIVE:
            return True, f"Destructive step '{step.title}' requires explicit human approval."

        # 2. Explicit step-level flag
        if step.approval_required:
            return True, f"Step '{step.title}' has explicit approval requirement."

        # 3. Project policy constraints
        if project_policy == "READ_ONLY" and step.risk_level != TaskRiskLevel.READ:
            return True, f"Project is in READ_ONLY mode. Write action '{step.title}' requires approval."

        # 4. Autonomy level evaluation
        if autonomy_level == AutonomyLevel.ASSISTED:
            return True, f"Autonomy level is ASSISTED; confirmation required for step '{step.title}'."

        if autonomy_level == AutonomyLevel.SUPERVISED:
            if step.risk_level in (TaskRiskLevel.WRITE, TaskRiskLevel.DESTRUCTIVE):
                return True, f"SUPERVISED mode requires approval for write action '{step.title}'."
            return False, ""

        if autonomy_level == AutonomyLevel.AUTONOMOUS_READ:
            if step.risk_level != TaskRiskLevel.READ:
                return True, f"AUTONOMOUS_READ does not permit autonomous write action '{step.title}'."
            return False, ""

        if autonomy_level == AutonomyLevel.AUTONOMOUS_BOUNDED:
            # Low/medium writes proceed if explicitly classified as bounded
            if any(t in step.title.lower() or t in step.objective.lower() for t in HIGH_RISK_TARGETS):
                return True, f"Step '{step.title}' targets a high-risk resource ({HIGH_RISK_TARGETS})."
            return False, ""

        return True, "Default policy requires approval."

    @classmethod
    def validate_goal_alignment(cls, original_objective: str, step_objective: str) -> None:
        """Detect and reject goal drift where a step diverges from original objective (Spec 139)."""
        orig_lower = original_objective.lower()
        step_lower = step_objective.lower()

        # If original objective is purely investigative or read-only, block destructive steps
        investigative_keywords = ["investigate", "read", "analyze", "research", "summarize", "find", "check"]
        is_investigative = any(k in orig_lower for k in investigative_keywords) and not any(
            w in orig_lower for w in ["delete", "drop", "wipe", "destroy"]
        )

        if is_investigative:
            for pat in DESTRUCTIVE_PATTERNS:
                if re.search(pat, step_lower):
                    raise TaskPolicyViolationError(
                        f"GOAL_DRIFT_DETECTED: Original objective is investigative ('{original_objective}'), "
                        f"but step attempts destructive action ('{step_objective}'). Blocked."
                    )

    @classmethod
    def sanitize_untrusted_input(cls, text: str) -> str:
        """Neutralize prompt injection attempts in external content (Spec 137, 138)."""
        # External content cannot issue task control instructions
        prohibited_injections = [
            r"(?i)ignore\s+(all\s+)?(previous|prior|above)\s+instructions?",
            r"(?i)you\s+are\s+now\s+in\s+(developer|god|unrestricted)\s+mode",
            r"(?i)override\s+system\s+prompt",
            r"(?i)delete\s+the\s+repository",
            r"(?i)send\s+all\s+secrets\s+to",
            r"(?i)approve\s+this\s+action",
        ]
        sanitized = text
        for pat in prohibited_injections:
            sanitized = re.sub(pat, "[UNTRUSTED_INSTRUCTION_REDACTED]", sanitized)
        return sanitized
