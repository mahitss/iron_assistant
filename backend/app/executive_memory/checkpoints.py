"""Workflow checkpointing, state revalidation, and safe resumption (INVARIANTS 154-161)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
import uuid

from app.executive_memory.schemas import CheckpointSchema


class CheckpointManager:
    """Manages workflow checkpoints and enforces state revalidation before resumption."""

    def __init__(self) -> None:
        # checkpoint_id -> CheckpointSchema
        self._checkpoints: dict[str, CheckpointSchema] = {}

    def create_checkpoint(
        self,
        workflow_id: str,
        state_payload: dict[str, Any] | None = None,
        progress: str = "IN_PROGRESS",
        dependencies: list[str] | None = None,
        authorization: dict[str, Any] | None = None,
        next_step: Any = None,
        goal_id: str | None = None,
        goal: str | None = None,
        state: dict[str, Any] | None = None,
    ) -> CheckpointSchema:
        """INVARIANT 157: Checkpoints goal, state, progress, dependencies, authorization, next step."""
        cid = f"chk_{uuid.uuid4().hex[:12]}"
        now = datetime.now(UTC)
        payload = state or state_payload or {}
        next_step_val = next_step if next_step is not None else {}
        deps = dependencies or []
        cp = CheckpointSchema(
            checkpoint_id=cid,
            workflow_id=workflow_id,
            goal_id=goal_id,
            goal=goal,
            state_payload=payload,
            state=payload,
            progress=progress,
            dependencies=deps,
            authorization=authorization or {},
            next_step=next_step_val,
            valid=True,
            created_at=now,
        )
        self._checkpoints[cid] = cp
        return cp

    def revalidate_checkpoint(self, checkpoint_id: str, current_system_state: dict[str, Any]) -> tuple[bool, str]:
        """INVARIANT 155 & 158: Revalidates checkpoint against current state before resumption."""
        cp = self._checkpoints.get(checkpoint_id)
        if not cp:
            return False, "Checkpoint not found"
        if not cp.valid:
            return False, "Checkpoint has been invalidated"

        # Check dependencies
        active_deps = current_system_state.get("dependencies_active")
        for dep in cp.dependencies:
            if active_deps is not None:
                if dep not in active_deps:
                    return False, f"Unsatisfied dependencies: '{dep}'"
            elif not current_system_state.get(dep, True):
                return False, f"Unsatisfied dependencies: '{dep}'"

        return True, "Checkpoint valid for resumption"

    def resume(
        self,
        checkpoint_id: str,
        current_authoritative_state: dict[str, Any],
    ) -> dict[str, Any]:
        """INVARIANTS 154-158: Revalidates checkpoint against current state and resumes."""
        cp = self._checkpoints.get(checkpoint_id)
        if not cp:
            raise KeyError(f"Checkpoint '{checkpoint_id}' not found.")
        valid, reason = self.revalidate_checkpoint(checkpoint_id, current_authoritative_state)
        if not valid:
            raise ValueError(f"Unsatisfied dependencies: {reason}")
        return {
            "status": "RESUMED",
            "checkpoint_id": checkpoint_id,
            "next_step": cp.next_step,
            "state": cp.state_payload or cp.state,
        }

    def invalidate_checkpoint(self, checkpoint_id: str) -> None:
        """INVARIANT 160: Cancelled work must not silently resume."""
        cp = self._checkpoints.get(checkpoint_id)
        if cp:
            cp.valid = False
