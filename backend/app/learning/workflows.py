"""Workflow pattern learning, versioning, promotion, and safety re-checks (INVARIANTS 62-67)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
import uuid

from app.learning.schemas import WorkflowPatternSchema


class WorkflowPolicyViolationError(Exception):
    """Raised when an existing workflow violates current system policies upon re-check."""
    pass


class WorkflowManager:
    """Manages creation, promotion, deprecation, and policy re-validation of learned workflows."""

    def __init__(self) -> None:
        # workflow_id -> WorkflowPatternSchema
        self._workflows: dict[str, WorkflowPatternSchema] = {}

    def register_workflow(
        self,
        name: str,
        steps: list[dict[str, Any]],
        preconditions: list[dict[str, Any]] | None = None,
        expected_outcome: dict[str, Any] | None = None,
        verification: dict[str, Any] | None = None,
        failure_modes: list[str] | None = None,
        version: str = "1.0.0",
    ) -> WorkflowPatternSchema:
        """INVARIANT 62 & 63: Models reusable workflows with preconditions, steps, outcome, verification, and failure modes."""
        wid = f"wf_{uuid.uuid4().hex[:12]}"
        now = datetime.now(UTC)
        workflow = WorkflowPatternSchema(
            workflow_id=wid,
            name=name.strip(),
            version=version,
            preconditions=preconditions or [],
            steps=steps,
            expected_outcome=expected_outcome or {},
            verification=verification or {},
            failure_modes=failure_modes or [],
            success_count=0,
            failure_count=0,
            status="CANDIDATE",
            created_at=now,
            updated_at=now,
        )
        self._workflows[wid] = workflow
        return workflow

    def promote_workflow(self, workflow_id: str, min_successes: int = 3) -> WorkflowPatternSchema:
        """INVARIANT 64: Promote only after repeated or explicitly validated success."""
        wf = self._workflows.get(workflow_id)
        if not wf:
            raise ValueError(f"Workflow '{workflow_id}' not found.")

        if wf.success_count < min_successes:
            raise ValueError(
                f"INVARIANT 64: Cannot promote workflow with only {wf.success_count} success(es). "
                f"Requires at least {min_successes} verified executions."
            )

        wf.status = "ACTIVE"
        wf.updated_at = datetime.now(UTC)
        return wf

    def deprecate_workflow(self, workflow_id: str, reason: str) -> WorkflowPatternSchema:
        """INVARIANT 66: Deprecates old workflows."""
        wf = self._workflows.get(workflow_id)
        if not wf:
            raise ValueError(f"Workflow '{workflow_id}' not found.")

        wf.status = "DEPRECATED"
        wf.failure_modes.append(f"Deprecation reason: {reason}")
        wf.updated_at = datetime.now(UTC)
        return wf

    def record_execution_outcome(self, workflow_id: str, was_successful: bool) -> None:
        wf = self._workflows.get(workflow_id)
        if wf:
            if was_successful:
                wf.success_count += 1
            else:
                wf.failure_count += 1
            wf.updated_at = datetime.now(UTC)

    def validate_workflow_against_policy(
        self,
        workflow_id: str,
        active_policy_checker: Any,
    ) -> bool:
        """INVARIANT 67: Stored workflow must re-check current active policy before execution."""
        wf = self._workflows.get(workflow_id)
        if not wf:
            raise ValueError(f"Workflow '{workflow_id}' not found.")

        for step in wf.steps:
            action_name = step.get("action", "")
            if active_policy_checker and not active_policy_checker(action_name):
                raise WorkflowPolicyViolationError(
                    f"INVARIANT 67: Workflow '{wf.name}' step '{action_name}' violates current active policy. Execution blocked."
                )
        return True

    def get_workflow(self, workflow_id: str) -> WorkflowPatternSchema | None:
        return self._workflows.get(workflow_id)

    def list_workflows(self, status: str | None = None) -> list[WorkflowPatternSchema]:
        results = list(self._workflows.values())
        if status:
            results = [w for w in results if w.status == status]
        return results
