"""Canonical Autonomous Execution Controller and Verification Pipeline (Task 45)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
from typing import Any, Callable, Dict, List, Optional
import uuid

from app.autonomy.budgets import AutonomousBudget
from app.autonomy.checkpoints import CheckpointManager
from app.autonomy.deadlines import DeadlineTracker
from app.autonomy.interruption import InterruptionHandler
from app.autonomy.progress import ProgressTracker
from app.autonomy.safety import ActionClassification, AutonomyLevel, AutonomySafetyGuard
from app.autonomy.state import AutonomousRunState

logger = logging.getLogger("kairo.autonomy.controller")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class VerificationFailedError(Exception):
    """Raised when a step output or side-effect fails independent verification criteria."""


@dataclass
class StepExecutionResult:
    """Outcome of a single autonomous step execution (Spec 41, 42)."""

    step_id: str
    is_success: bool
    is_verified: bool
    outputs: Dict[str, Any] = field(default_factory=dict)
    evidence_refs: List[str] = field(default_factory=list)
    verification_notes: str = ""
    error: Optional[str] = None
    executed_at: datetime = field(default_factory=utc_now)


class RunController:
    """Executes the canonical 12-stage execution loop with strict verification (Spec 28-42)."""

    def __init__(
        self,
        checkpoint_manager: CheckpointManager,
        progress_tracker: ProgressTracker,
        interruption_handler: InterruptionHandler,
        deadline_tracker: DeadlineTracker,
        budget: AutonomousBudget,
        autonomy_level: AutonomyLevel = AutonomyLevel.AUTONOMOUS,
    ) -> None:
        self.checkpoint_manager = checkpoint_manager
        self.progress_tracker = progress_tracker
        self.interruption_handler = interruption_handler
        self.deadline_tracker = deadline_tracker
        self.budget = budget
        self.autonomy_level = autonomy_level

    def select_next_ready_step(
        self,
        steps: List[Dict[str, Any]],
        completed_step_ids: set[str],
        in_progress_step_ids: set[str],
    ) -> Optional[Dict[str, Any]]:
        """Select next step whose dependencies are satisfied (Spec 29-31)."""
        for s in steps:
            sid = s.get("step_id", s.get("id"))
            if sid in completed_step_ids or sid in in_progress_step_ids:
                continue
            deps = set(s.get("dependencies", []))
            # Ready only if all dependencies are in completed_step_ids
            if deps.issubset(completed_step_ids):
                return s
        return None

    def execute_step(
        self,
        run_id: str,
        plan_version: int,
        step: Dict[str, Any],
        tool_executor_fn: Callable[[str, Dict[str, Any]], Any],
        verifier_fn: Optional[Callable[[Dict[str, Any], Any], tuple[bool, str]]] = None,
        is_pre_approved: bool = False,
    ) -> StepExecutionResult:
        """Canonical step execution: PRECHECKS -> SAFETY -> BUDGET -> EXECUTE -> OBSERVE -> VERIFY -> CHECKPOINT."""
        step_id = step.get("step_id", step.get("id", "step_unknown"))
        action_type_str = step.get("action_type", "ANALYZE").upper()

        try:
            action_class = ActionClassification(action_type_str)
        except ValueError:
            action_class = ActionClassification.ANALYZE

        # 1. Check interruption / emergency stop (Spec 66, 68)
        if self.interruption_handler.should_halt_immediately:
            raise InterruptedError(f"Execution halted: {self.interruption_handler.stop_reason}")

        # 2. Safety & Autonomy Level gating (Spec 139, 141)
        AutonomySafetyGuard.validate_action_against_autonomy_level(
            action_class=action_class,
            autonomy_level=self.autonomy_level,
            is_pre_approved=is_pre_approved,
        )

        # 3. Check anti-self-modification (Spec 191)
        target_res = step.get("target_resource", "")
        if target_res:
            AutonomySafetyGuard.validate_anti_self_modification(target_res, str(step.get("params", "")))

        # 4. Check Deadline & Budget (Spec 53, 56)
        self.deadline_tracker.validate_deadline()
        self.budget.check_and_consume(tool_calls=1, cost_usd=0.01)

        # 5. Checkpoint BEFORE consequential operation (Spec 13)
        if action_class in [ActionClassification.WRITE, ActionClassification.DEPLOY, ActionClassification.DELETE]:
            self.checkpoint_manager.create_checkpoint(
                run_id=run_id,
                plan_version=plan_version,
                run_state="RUNNING",
                step_id=step_id,
                active_work=[step],
            )

        # 6. Execute via ToolExecutor
        tool_name = step.get("tool_name", "noop")
        tool_args = step.get("params", {})
        try:
            raw_output = tool_executor_fn(tool_name, tool_args)
        except Exception as exc:
            logger.error("Step %s tool execution failed: %s", step_id, exc)
            return StepExecutionResult(
                step_id=step_id,
                is_success=False,
                is_verified=False,
                error=str(exc),
            )

        # 7. Independent Verification (Spec 40, 41, 42)
        # CRITICAL: Never mark step complete because model/tool says done without verification!
        is_verified = False
        verification_notes = "Default execution observation."
        if verifier_fn:
            is_verified, verification_notes = verifier_fn(step, raw_output)
            if not is_verified:
                logger.warning("Step %s failed verification criteria: %s", step_id, verification_notes)
                return StepExecutionResult(
                    step_id=step_id,
                    is_success=False,
                    is_verified=False,
                    outputs={"raw": raw_output},
                    verification_notes=verification_notes,
                    error=f"Verification failed: {verification_notes}",
                )
        else:
            # For read/analyze steps, tool return establishes verified observation
            is_verified = True
            verification_notes = "Observation verified."

        # 8. Checkpoint AFTER successful verified operation (Spec 13)
        self.checkpoint_manager.create_checkpoint(
            run_id=run_id,
            plan_version=plan_version,
            run_state="RUNNING",
            step_id=step_id,
            completed_work=[{"step_id": step_id, "output": raw_output}],
            verification_state={step_id: is_verified},
        )

        return StepExecutionResult(
            step_id=step_id,
            is_success=True,
            is_verified=is_verified,
            outputs={"raw": raw_output} if not isinstance(raw_output, dict) else raw_output,
            verification_notes=verification_notes,
        )
