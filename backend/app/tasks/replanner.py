"""Intelligent failure classification, retries, replanning, and oscillation detection (Spec 31-37, 76, 100-102)."""

import hashlib
import json
import logging
from typing import Any, Dict, List, Optional, Set, Tuple

from app.config.settings import get_settings
from app.tasks.schemas import (
    FailureClassification,
    StepStatus,
    TaskPlanSchema,
    TaskRiskLevel,
    TaskStepSchema,
)

logger = logging.getLogger("kairo.tasks.replanner")


class LoopDetectedError(RuntimeError):
    """Raised when an autonomous task detects an execution loop or plan oscillation."""

    def __init__(self, message: str) -> None:
        super().__init__(f"LOOP_DETECTED: {message}")


class TaskReplanner:
    """Manages failure classification, retries, plan versioning, and loop/oscillation prevention."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.max_retries = getattr(self.settings, "KAIRO_TASK_MAX_RETRIES", 3)
        self._seen_plan_hashes: dict[str, list[str]] = {}  # task_id -> list of plan_hash strings
        self._repeated_tool_attempts: dict[str, int] = {}  # task_id:step_id:tool -> count

    @classmethod
    def classify_failure(cls, error_text: str) -> FailureClassification:
        """Deterministically categorize error into root-cause failure class (Spec 31)."""
        err_lower = (error_text or "").lower()

        if any(w in err_lower for w in ["timeout", "timed out", "deadline"]):
            return FailureClassification.TIMEOUT
        if any(w in err_lower for w in ["budget", "budget_exceeded", "limit exhausted"]):
            return FailureClassification.BUDGET
        if any(w in err_lower for w in ["security", "security_blocked", "denied by policy"]):
            return FailureClassification.SECURITY
        if any(w in err_lower for w in ["unauthorized", "permission denied", "forbidden", "401", "403"]):
            return FailureClassification.AUTHORIZATION
        if any(w in err_lower for w in ["rate limit", "429", "too many requests", "connection reset", "econnreset", "transient"]):
            return FailureClassification.TRANSIENT
        if any(w in err_lower for w in ["dependency", "missing step", "circular"]):
            return FailureClassification.DEPENDENCY
        if any(w in err_lower for w in ["capability", "tool unavailable", "skill unavailable"]):
            return FailureClassification.CAPABILITY
        if any(w in err_lower for w in ["verification", "assertion", "test failed"]):
            return FailureClassification.VALIDATION
        if any(w in err_lower for w in ["user cancelled", "user intervention"]):
            return FailureClassification.USER

        return FailureClassification.UNKNOWN

    def should_retry_step(
        self,
        step: TaskStepSchema,
        classification: FailureClassification,
    ) -> Tuple[bool, float]:
        """Determine if a failed step is eligible for automatic retry (Spec 32, 33).

        Rules:
        - NEVER retry destructive writes or security blocks.
        - Only TRANSIENT or temporary network/rate-limit failures may be retried.
        - Bounded by max_retries with exponential backoff (e.g., 2^retry_count seconds).
        """
        # Hard invariants:
        if step.risk_level == TaskRiskLevel.DESTRUCTIVE:
            return False, 0.0
        if classification in (
            FailureClassification.SECURITY,
            FailureClassification.AUTHORIZATION,
            FailureClassification.BUDGET,
            FailureClassification.TIMEOUT,
        ):
            return False, 0.0

        if classification == FailureClassification.TRANSIENT:
            if step.retry_count < self.max_retries:
                delay = 2 ** step.retry_count
                return True, float(delay)

        return False, 0.0

    @classmethod
    def compute_plan_hash(cls, steps: list[TaskStepSchema]) -> str:
        """Compute stable hash of plan step sequence and objectives (Spec 101)."""
        normalized = [
            {"seq": s.sequence, "title": s.title.strip().lower(), "deps": sorted(s.dependencies)}
            for s in steps
        ]
        raw = json.dumps(normalized, sort_keys=True)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

    def record_and_verify_plan_oscillation(self, task_id: str, plan_hash: str) -> None:
        """Detect and block plan oscillation (e.g. Plan A -> Plan B -> Plan A) (Spec 101)."""
        if task_id not in self._seen_plan_hashes:
            self._seen_plan_hashes[task_id] = []

        history = self._seen_plan_hashes[task_id]
        if plan_hash in history:
            # Oscillation detected!
            raise LoopDetectedError(
                f"Plan oscillation detected for task {task_id}. "
                f"Plan hash '{plan_hash}' was previously generated and failed."
            )

        history.append(plan_hash)

    def record_tool_execution(self, task_id: str, step_id: str, tool_name: str) -> None:
        """Detect repeating identical tool calls without state change (Spec 100, 102)."""
        key = f"{task_id}:{step_id}:{tool_name}"
        count = self._repeated_tool_attempts.get(key, 0) + 1
        self._repeated_tool_attempts[key] = count

        if count > 4:
            raise LoopDetectedError(
                f"Tool oscillation detected: Tool '{tool_name}' invoked {count} times repeatedly without progress."
            )

    def generate_alternative_step_plan(
        self,
        current_plan: TaskPlanSchema,
        failed_step: TaskStepSchema,
        alternative_tool: str | None = None,
        alternative_skill: str | None = None,
    ) -> TaskPlanSchema:
        """Produce a new versioned TaskPlan with a recovered or alternative step (Spec 37, 76)."""
        new_version = current_plan.version + 1
        new_steps: list[TaskStepSchema] = []

        for s in current_plan.steps:
            if s.id == failed_step.id:
                # Replace with alternative step or reset for alternative tool
                alt_step = TaskStepSchema(
                    id=f"{s.id}_v{new_version}",
                    task_id=s.task_id,
                    plan_id=f"plan_{s.task_id}_{new_version}",
                    sequence=s.sequence,
                    title=f"{s.title} (Alternative)",
                    objective=s.objective,
                    skill_id=alternative_skill or s.skill_id,
                    tool_name=alternative_tool or s.tool_name,
                    arguments=s.arguments,
                    dependencies=s.dependencies,
                    status=StepStatus.PENDING,
                    risk_level=s.risk_level,
                    approval_required=s.approval_required,
                    retry_count=0,
                    resources=s.resources,
                )
                new_steps.append(alt_step)
            else:
                # Update dependencies if pointing to old failed step
                deps = [
                    f"{d}_v{new_version}" if d == failed_step.id else d
                    for d in s.dependencies
                ]
                new_steps.append(
                    TaskStepSchema(
                        id=s.id,
                        task_id=s.task_id,
                        plan_id=f"plan_{s.task_id}_{new_version}",
                        sequence=s.sequence,
                        title=s.title,
                        objective=s.objective,
                        skill_id=s.skill_id,
                        tool_name=s.tool_name,
                        arguments=s.arguments,
                        dependencies=deps,
                        status=s.status,
                        risk_level=s.risk_level,
                        approval_required=s.approval_required,
                        retry_count=s.retry_count,
                        resources=s.resources,
                        result_reference=s.result_reference,
                    )
                )

        new_plan_hash = self.compute_plan_hash(new_steps)
        self.record_and_verify_plan_oscillation(current_plan.task_id, new_plan_hash)

        return TaskPlanSchema(
            id=f"plan_{current_plan.task_id}_{new_version}",
            task_id=current_plan.task_id,
            version=new_version,
            plan_hash=new_plan_hash,
            steps=new_steps,
            verification_criteria=current_plan.verification_criteria,
            supersedes_plan_id=current_plan.id,
        )
