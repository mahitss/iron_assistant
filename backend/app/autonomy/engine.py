"""Master Autonomous Execution and Long-Horizon Agency Engine (Task 45)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import logging
from typing import Any, Callable, Dict, List, Optional
import uuid

from app.autonomy.budgets import AutonomousBudget, BudgetExhaustedError
from app.autonomy.checkpoints import AutonomousCheckpoint, CheckpointManager
from app.autonomy.controller import RunController, StepExecutionResult
from app.autonomy.deadlines import DeadlineTracker
from app.autonomy.escalation import EscalationManager
from app.autonomy.execution import (
    AutonomousExecutionLoop,
    ExecutionResourceManager,
    OutcomeCertainty,
    SideEffectRetryViolationError,
)
from app.autonomy.goals import AutonomousGoal, GoalDriftError, GoalManager
from app.autonomy.heartbeat import HeartbeatTracker
from app.autonomy.interruption import InterruptionHandler
from app.autonomy.leases import ExecutionLeaseManager
from app.autonomy.lifecycle import RunLifecycleManager, WaitConditionType
from app.autonomy.persistence import AutonomyPersistenceManager
from app.autonomy.policies import AutonomyPolicyEngine, DomainWorkflowType
from app.autonomy.progress import ProgressSnapshot, ProgressTracker
from app.autonomy.recovery import RecoveryDecision, RecoveryEngine
from app.autonomy.replanning import PlanDiff, ReplanningManager
from app.autonomy.safety import ActionClassification, AutonomyLevel, AutonomySafetyGuard
from app.autonomy.scheduler import AutonomousScheduler, CorrelatedEvent
from app.autonomy.sessions import AutonomousScope, AutonomousSession
from app.autonomy.state import AutonomousRunState, can_transition
from app.autonomy.watchdog import AutonomyWatchdog

logger = logging.getLogger("kairo.autonomy.engine")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class FalseCompletionError(Exception):
    """Raised when an attempt is made to mark a run or goal complete without verified criteria."""


@dataclass
class CompletionRecord:
    """Immutable certificate of verified goal completion (Spec 155, 156)."""

    record_id: str
    run_id: str
    goal_id: str
    plan_version: int
    success_criteria: List[str]
    verification_results: List[str]
    evidence_refs: List[str]
    remaining_uncertainty: List[str]
    completed_at: datetime = field(default_factory=utc_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_id": self.record_id,
            "run_id": self.run_id,
            "goal_id": self.goal_id,
            "plan_version": self.plan_version,
            "success_criteria": self.success_criteria,
            "verification_results": self.verification_results,
            "evidence_refs": self.evidence_refs,
            "remaining_uncertainty": self.remaining_uncertainty,
            "completed_at": self.completed_at.isoformat(),
        }


@dataclass
class AutonomousRun:
    """Active instance of an autonomous execution lifecycle (Spec 2, 3)."""

    run_id: str
    goal_id: str
    plan_id: str
    plan_version: int
    status: AutonomousRunState
    autonomy_level: AutonomyLevel
    owner_user_id: str
    project_id: str
    steps: List[Dict[str, Any]] = field(default_factory=list)
    current_step_id: Optional[str] = None
    completed_step_ids: set[str] = field(default_factory=set)
    in_progress_step_ids: set[str] = field(default_factory=set)
    budget: AutonomousBudget = field(default_factory=AutonomousBudget)
    deadline_tracker: DeadlineTracker = field(default_factory=DeadlineTracker)
    progress_pct: float = 0.0
    session_id: Optional[str] = None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "goal_id": self.goal_id,
            "plan_id": self.plan_id,
            "plan_version": self.plan_version,
            "status": self.status.value,
            "autonomy_level": self.autonomy_level.value,
            "owner_user_id": self.owner_user_id,
            "project_id": self.project_id,
            "current_step_id": self.current_step_id,
            "progress_pct": self.progress_pct,
            "session_id": self.session_id,
            "budget": self.budget.to_dict(),
            "deadline": self.deadline_tracker.to_dict(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class AutonomousExecutionEngine:
    """Master long-horizon agency coordinator governing goals, plans, checkpoints, and recovery."""

    def __init__(self) -> None:
        self.goal_manager = GoalManager()
        self.checkpoint_manager = CheckpointManager()
        self.lease_manager = ExecutionLeaseManager()
        self.heartbeat_tracker = HeartbeatTracker()
        self.watchdog = AutonomyWatchdog(self.lease_manager, self.heartbeat_tracker)
        self.recovery_engine = RecoveryEngine(self.checkpoint_manager)
        self.replanning_manager = ReplanningManager()
        self.progress_tracker = ProgressTracker()
        self.escalation_manager = EscalationManager()
        self.lifecycle_manager = RunLifecycleManager()
        self.scheduler = AutonomousScheduler()
        self.policy_engine = AutonomyPolicyEngine()
        self.resource_manager = ExecutionResourceManager()
        self.persistence_manager = AutonomyPersistenceManager()

        # In-memory runs index: run_id -> AutonomousRun
        self._runs: Dict[str, AutonomousRun] = {}
        # run_id -> InterruptionHandler
        self._interrupt_handlers: Dict[str, InterruptionHandler] = {}
        # run_id -> CompletionRecord
        self._completion_records: Dict[str, CompletionRecord] = {}
        # session_id -> AutonomousSession
        self._sessions: Dict[str, AutonomousSession] = {}

    def create_session(
        self,
        user_id: str,
        project_id: str,
        goal_id: str,
        scope: Optional[AutonomousScope] = None,
    ) -> AutonomousSession:
        """Create and track an authorized autonomous execution session (Spec 4, 125-128)."""
        session_id = f"sess_{uuid.uuid4().hex[:12]}"
        session = AutonomousSession(
            session_id=session_id,
            user_id=user_id,
            project_id=project_id,
            goal_id=goal_id,
            scope=scope or AutonomousScope(),
        )
        self._sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> Optional[AutonomousSession]:
        return self._sessions.get(session_id)

    def create_run(
        self,
        goal_id: str,
        owner_user_id: str,
        project_id: str = "default_project",
        autonomy_level: AutonomyLevel = AutonomyLevel.AUTONOMOUS,
        initial_steps: Optional[List[Dict[str, Any]]] = None,
        budget: Optional[AutonomousBudget] = None,
        deadline: Optional[datetime] = None,
        session_id: Optional[str] = None,
    ) -> AutonomousRun:
        """Instantiate an autonomous run for an authorized goal."""
        goal = self.goal_manager.get_goal(goal_id)
        if not goal:
            raise KeyError(f"Goal {goal_id} not registered.")

        # Ensure valid session
        if not session_id:
            sess = self.create_session(user_id=owner_user_id, project_id=project_id, goal_id=goal_id)
            session_id = sess.session_id

        run_id = f"run_{uuid.uuid4().hex[:12]}"
        run = AutonomousRun(
            run_id=run_id,
            goal_id=goal_id,
            plan_id=f"plan_{uuid.uuid4().hex[:8]}",
            plan_version=1,
            status=AutonomousRunState.INITIALIZING,
            autonomy_level=autonomy_level,
            owner_user_id=owner_user_id,
            project_id=project_id,
            steps=initial_steps or [],
            budget=budget or AutonomousBudget(),
            deadline_tracker=DeadlineTracker(deadline),
            session_id=session_id,
        )

        self._runs[run_id] = run
        self._interrupt_handlers[run_id] = InterruptionHandler()
        self.lease_manager.acquire_lease(run_id=run_id, worker_id=owner_user_id)
        self.heartbeat_tracker.record_heartbeat(run_id=run_id, worker_id=owner_user_id)

        # Checkpoint initial state (Spec 10)
        self.checkpoint_manager.create_checkpoint(
            run_id=run_id,
            plan_version=1,
            run_state=run.status.value,
            pending_work=run.steps,
        )

        run.status = AutonomousRunState.RUNNING
        logger.info("Initialized autonomous run %s for goal %s (autonomy=%s)", run_id, goal_id, autonomy_level.value)
        return run

    def get_run(self, run_id: str) -> Optional[AutonomousRun]:
        return self._runs.get(run_id)

    def execute_next_step(
        self,
        run_id: str,
        tool_executor_fn: Callable[[str, Dict[str, Any]], Any],
        verifier_fn: Optional[Callable[[Dict[str, Any], Any], tuple[bool, str]]] = None,
        state_inspector_fn: Optional[Callable[[str, Dict[str, Any]], bool]] = None,
        is_pre_approved: bool = False,
        is_dry_run: bool = False,
    ) -> Optional[StepExecutionResult]:
        """Fetch next ready step from DAG, validate policies/preconditions, execute, verify, and checkpoint."""
        run = self._runs.get(run_id)
        if not run:
            raise KeyError(f"Run {run_id} not found.")

        if run.status != AutonomousRunState.RUNNING:
            logger.warning("Cannot execute step: Run %s is in state %s", run_id, run.status.value)
            return None

        # 1. Select ready step using DAG scheduler (Spec 29-31)
        ready = self.scheduler.get_ready_steps(run.steps, run.completed_step_ids, run.in_progress_step_ids)
        if not ready:
            logger.info("No ready steps for run %s (all done or blocked)", run_id)
            return None

        step = ready[0]
        step_id = step.get("step_id", step.get("id", "step_unknown"))
        run.current_step_id = step_id
        run.in_progress_step_ids.add(step_id)

        # 2. Setup controller and execution loop
        controller = RunController(
            checkpoint_manager=self.checkpoint_manager,
            progress_tracker=self.progress_tracker,
            interruption_handler=self._interrupt_handlers[run_id],
            deadline_tracker=run.deadline_tracker,
            budget=run.budget,
            autonomy_level=run.autonomy_level,
        )
        loop = AutonomousExecutionLoop(
            controller=controller,
            resource_manager=self.resource_manager,
            is_dry_run=is_dry_run,
        )

        try:
            # 3. Policy pre-check (Spec 37, 176)
            action_type_str = step.get("action_type", "ANALYZE").upper()
            try:
                action_class = ActionClassification(action_type_str)
            except ValueError:
                action_class = ActionClassification.ANALYZE

            self.policy_engine.evaluate_action_policy(
                action_class=action_class,
                target_resource=step.get("target_resource", ""),
                params=step.get("params", {}),
                is_approval_present=is_pre_approved,
            )

            # 4. Execute safely
            result = loop.execute_step_safely(
                run_id=run_id,
                plan_version=run.plan_version,
                step=step,
                tool_executor_fn=tool_executor_fn,
                state_inspector_fn=state_inspector_fn,
                verifier_fn=verifier_fn,
                is_pre_approved=is_pre_approved,
            )

            if result.is_success and result.is_verified:
                run.completed_step_ids.add(step_id)
                # Track progress (Spec 57-61)
                goal = self.goal_manager.get_goal(run.goal_id)
                crit_count = len(goal.success_criteria) if goal else 1
                prog = self.progress_tracker.calculate_progress(
                    total_steps=len(run.steps),
                    completed_steps=len(run.completed_step_ids),
                    total_criteria=crit_count,
                    verified_criteria=min(crit_count, len(run.completed_step_ids)),
                    verified_artifacts=len(result.evidence_refs),
                )
                run.progress_pct = prog.percentage
                self.progress_tracker.record_step_execution(step_id, len(run.completed_step_ids))

            run.updated_at = utc_now()
            return result

        finally:
            run.in_progress_step_ids.discard(step_id)

    def pause_run(self, run_id: str, reason: str = "User pause") -> None:
        """Pause run safely before starting next consequential operation (Spec 65-67)."""
        run = self._runs.get(run_id)
        if not run:
            raise KeyError(f"Run {run_id} not found.")

        handler = self._interrupt_handlers.get(run_id)
        if handler:
            handler.request_pause()

        run.status = AutonomousRunState.PAUSED
        run.updated_at = utc_now()
        logger.info("Paused run %s: %s", run_id, reason)

    def resume_run(
        self,
        run_id: str,
        current_world_state_version: Optional[str] = None,
        is_authorization_valid: bool = True,
    ) -> RecoveryDecision:
        """Resume run after verifying state, plan freshness, and authorization (Spec 14-19, 71)."""
        run = self._runs.get(run_id)
        if not run:
            raise KeyError(f"Run {run_id} not found.")

        # Revalidate state and authorization
        decision = self.recovery_engine.plan_recovery(
            run_id=run_id,
            current_world_state_version=current_world_state_version,
            is_authorization_valid=is_authorization_valid,
        )

        if decision.action == "RESUME":
            handler = self._interrupt_handlers.get(run_id)
            if handler:
                handler.clear_pause()
            run.status = AutonomousRunState.RUNNING
        elif decision.action == "REPLAN":
            run.status = AutonomousRunState.REPLANNING
        else:
            run.status = AutonomousRunState.BLOCKED

        run.updated_at = utc_now()
        return decision

    def cancel_run(self, run_id: str, reason: str = "User cancelled") -> None:
        """Safely cancel future work while preserving completed work and evidence (Spec 69, 70)."""
        run = self._runs.get(run_id)
        if not run:
            raise KeyError(f"Run {run_id} not found.")

        handler = self._interrupt_handlers.get(run_id)
        if handler:
            handler.request_cancel(reason)

        run.status = AutonomousRunState.CANCELLED
        run.updated_at = utc_now()
        logger.info("Cancelled run %s: %s", run_id, reason)

    def emergency_stop_run(self, run_id: str, reason: str = "Emergency stop") -> None:
        """Immediate hard stop propagating to all child agents and tasks (Spec 68, 111, 112)."""
        run = self._runs.get(run_id)
        if not run:
            raise KeyError(f"Run {run_id} not found.")

        handler = self._interrupt_handlers.get(run_id)
        if handler:
            handler.trigger_emergency_stop(reason)

        run.status = AutonomousRunState.BLOCKED
        run.updated_at = utc_now()
        logger.critical("EMERGENCY STOP executed on run %s: %s", run_id, reason)

    def complete_run(
        self,
        run_id: str,
        verification_results: List[str],
        evidence_refs: List[str],
        remaining_uncertainty: Optional[List[str]] = None,
    ) -> CompletionRecord:
        """Certify goal completion with verified evidence (Spec 154-156).
        
        CRITICAL: Never claim completion without verified success criteria!
        """
        run = self._runs.get(run_id)
        if not run:
            raise KeyError(f"Run {run_id} not found.")

        goal = self.goal_manager.get_goal(run.goal_id)
        if not goal:
            raise KeyError(f"Goal {run.goal_id} not found.")

        # Require that all success criteria have verified proof
        if goal.success_criteria and len(verification_results) < len(goal.success_criteria):
            raise FalseCompletionError(
                f"Cannot complete run {run_id}: {len(goal.success_criteria)} success criteria required, but only {len(verification_results)} verified."
            )

        rec_id = f"comp_{uuid.uuid4().hex[:12]}"
        record = CompletionRecord(
            record_id=rec_id,
            run_id=run_id,
            goal_id=run.goal_id,
            plan_version=run.plan_version,
            success_criteria=goal.success_criteria,
            verification_results=verification_results,
            evidence_refs=evidence_refs,
            remaining_uncertainty=remaining_uncertainty or [],
        )
        self._completion_records[run_id] = record

        run.status = AutonomousRunState.COMPLETED
        run.progress_pct = 100.0
        run.updated_at = utc_now()

        # Checkpoint final completion state
        self.checkpoint_manager.create_checkpoint(
            run_id=run_id,
            plan_version=run.plan_version,
            run_state=run.status.value,
            evidence_refs=evidence_refs,
            verification_state={"verified_count": len(verification_results)},
        )
        logger.info("Run %s COMPLETED with verified certificate %s", run_id, rec_id)
        return record

    def get_completion_record(self, run_id: str) -> Optional[CompletionRecord]:
        return self._completion_records.get(run_id)
