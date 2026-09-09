"""Central Autonomous Task Engine implementing the bounded, verifiable execution loop (Spec 1, 22-26, 68-72, 117)."""

import asyncio
from datetime import UTC, datetime
import logging
import time
import uuid
from typing import Any, Dict, List, Optional, Set
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import get_settings
from app.events.bus import EventBus, get_event_bus
from app.events.schemas import Event, EventSource
from app.security.audit import AuditLogger
from app.tasks.budget import BudgetExceededError, TaskBudgetEnforcer
from app.tasks.cancellation import (
    CancellationToken,
    EmergencyStopActiveError,
    TaskCancelledError,
    get_cancellation_manager,
)
from app.tasks.checkpoint import CheckpointService
from app.tasks.dependencies import DependencyResolver
from app.tasks.executor import StepExecutor
from app.tasks.planner import TaskPlanner
from app.tasks.policies import TaskPolicyEngine, TaskPolicyViolationError
from app.tasks.replanner import LoopDetectedError, TaskReplanner
from app.tasks.resolver import TaskContextResolver
from app.tasks.scheduler import TaskScheduler, get_task_scheduler
from app.tasks.schemas import (
    AutonomyLevel,
    FailureClassification,
    StepStatus,
    TaskBudget,
    TaskPlanSchema,
    TaskResultSummary,
    TaskRiskLevel,
    TaskStatus,
    TaskStepSchema,
)
from app.tasks.state import TaskStateMachine
from app.tasks.verifier import TaskVerifier

logger = logging.getLogger("kairo.tasks.engine")


class AutonomousTaskEngine:
    """Core autonomous task execution coordinator."""

    def __init__(
        self,
        planner: TaskPlanner | None = None,
        executor: StepExecutor | None = None,
        replanner: TaskReplanner | None = None,
        scheduler: TaskScheduler | None = None,
        context_resolver: TaskContextResolver | None = None,
        event_bus: EventBus | None = None,
    ) -> None:
        self.settings = get_settings()
        self.planner = planner or TaskPlanner()
        self.executor = executor or StepExecutor()
        self.replanner = replanner or TaskReplanner()
        self.scheduler = scheduler or get_task_scheduler()
        self.context_resolver = context_resolver or TaskContextResolver()
        self.event_bus = event_bus or get_event_bus()
        self.cancellation_manager = get_cancellation_manager()
        self.max_parallel_steps = getattr(self.settings, "KAIRO_TASK_MAX_PARALLEL_STEPS", 4)

    async def run_task(
        self,
        task_id: str,
        user_id: str,
        objective: str,
        project_id: str | None = None,
        autonomy_level: AutonomyLevel = AutonomyLevel.SUPERVISED,
        budget: TaskBudget | None = None,
        deadline: datetime | None = None,
        dry_run: bool = False,
        session: AsyncSession | None = None,
    ) -> TaskResultSummary:
        """Execute the complete autonomous task lifecycle through the bounded loop."""
        start_time = datetime.now(UTC)
        correlation_id = f"corr_{uuid.uuid4().hex[:12]}"
        budget_enforcer = TaskBudgetEnforcer(budget)
        cancellation_token = self.cancellation_manager.get_or_create_token(task_id, user_id)

        # Register active task in scheduler fairness tracker
        self.scheduler.register_active_task(task_id, user_id, project_id)

        # State tracking
        current_status = TaskStatus.PLANNING
        completed_step_ids: Set[str] = set()
        step_results: dict[str, dict[str, Any]] = {}
        collected_evidence: list[dict[str, Any]] = []
        collected_artifacts: list[dict[str, Any]] = []
        applied_changes: list[dict[str, Any]] = []

        await self._publish_event("task.created", task_id, user_id, correlation_id, {"objective": objective})

        try:
            # 1. Resolve Initial Context (Spec 52)
            context = await self.context_resolver.resolve_initial_context(
                user_id=user_id, project_id=project_id, objective=objective, session=session
            )

            # 2. Generate Initial Plan (Spec 11, 12, 13)
            await self._publish_event("task.planning", task_id, user_id, correlation_id, {})
            current_plan = await self.planner.create_initial_plan(
                task_id=task_id,
                objective=objective,
                context=context,
                budget=budget_enforcer.current_budget,
            )

            current_status = TaskStatus.RUNNING
            await self._publish_event("task.started", task_id, user_id, correlation_id, {
                "plan_version": current_plan.version,
                "total_steps": len(current_plan.steps),
                "dry_run": dry_run,
            })

            # Main Autonomous Loop (Spec 22)
            while not TaskStateMachine.is_terminal(current_status):
                # A. Check Cancellation & Emergency Stop (Spec 42, 44)
                cancellation_token.check_cancelled()

                # B. Check Deadline (Spec 46)
                if deadline and datetime.now(UTC) > deadline:
                    current_status = TaskStatus.TIMED_OUT
                    await self._publish_event("task.timed_out", task_id, user_id, correlation_id, {"deadline": deadline.isoformat()})
                    break

                # C. Check Runtime Budget (Spec 15)
                budget_enforcer.check_limits()

                # D. Check if all plan steps are completed
                all_plan_step_ids = {s.id for s in current_plan.steps}
                if all_plan_step_ids.issubset(completed_step_ids):
                    # Verification Phase (Spec 27, 142)
                    current_status = TaskStatus.VERIFYING
                    all_results_list = list(step_results.values())
                    v_ok, v_report = await TaskVerifier.verify_task_completion(
                        task_objective=objective,
                        plan_criteria=current_plan.verification_criteria,
                        completed_step_results=all_results_list,
                    )
                    if v_ok:
                        current_status = TaskStatus.COMPLETED
                    else:
                        # Verification failed; trigger replan or mark partial (Spec 143)
                        current_status = TaskStatus.PARTIALLY_COMPLETED
                    break

                # E. Resolve Ready Steps (Spec 9, 23, 25)
                ready_steps = DependencyResolver.get_ready_steps(
                    steps=current_plan.steps,
                    completed_step_ids=completed_step_ids,
                    max_parallel=self.max_parallel_steps,
                )

                if not ready_steps:
                    # No ready steps could be found even though uncompleted steps remain
                    pending_unresolved = [s for s in current_plan.steps if s.id not in completed_step_ids]
                    if any(s.status == StepStatus.FAILED for s in current_plan.steps):
                        current_status = TaskStatus.FAILED
                    else:
                        current_status = TaskStatus.BLOCKED
                    break

                # F. Evaluate Step Approvals & Policies (Spec 18, 19, 149)
                steps_to_dispatch: list[TaskStepSchema] = []
                for step in ready_steps:
                    # Check approval
                    needs_approval, app_reason = TaskPolicyEngine.requires_approval(step, autonomy_level)
                    if needs_approval and not step.approval_id:
                        step.status = StepStatus.WAITING_APPROVAL
                        current_status = TaskStatus.WAITING_APPROVAL
                        await self._publish_event("task.waiting_approval", task_id, user_id, correlation_id, {
                            "step_id": step.id,
                            "action": step.title,
                            "target": str(step.arguments.get("target", "system")),
                            "risk": step.risk_level.value,
                            "reason": app_reason,
                        })
                        # Stop execution loop until user approves
                        return TaskResultSummary(
                            outcome=TaskStatus.WAITING_APPROVAL.value,
                            summary=f"Execution paused: Step '{step.title}' requires human approval ({app_reason}).",
                            evidence=collected_evidence,
                            artifacts=collected_artifacts,
                            changes=applied_changes,
                            verification={"status": "pending_approval", "step_id": step.id},
                            limitations=["Awaiting approval before mutating actions."],
                        )

                    # Central Policy Engine Governance Check (Task 36, Spec 98, 137)
                    from app.policy.engine import policy_engine
                    from app.policy.schemas import PolicyDecisionType
                    policy_dec = await policy_engine.check_task_step(
                        task_id=task_id,
                        action=step.tool_name or step.title,
                        target=step.arguments,
                        user_id=user_id,
                        tool_calls_count=len(completed_step_ids),
                    )
                    if policy_dec.decision == PolicyDecisionType.DENY:
                        step.status = StepStatus.FAILED
                        current_status = TaskStatus.FAILED
                        return TaskResultSummary(
                            outcome=TaskStatus.FAILED.value,
                            summary=f"Task step '{step.title}' blocked by governance policy: {policy_dec.safe_explanation}",
                            evidence=collected_evidence,
                            artifacts=collected_artifacts,
                            changes=applied_changes,
                            verification={"status": "policy_denied", "step_id": step.id, "reason": policy_dec.safe_explanation},
                            limitations=[f"Policy violation: {policy_dec.safe_explanation}"],
                        )
                    if policy_dec.decision == PolicyDecisionType.REQUIRE_APPROVAL and not step.approval_id:
                        step.status = StepStatus.WAITING_APPROVAL
                        current_status = TaskStatus.WAITING_APPROVAL
                        await self._publish_event("task.waiting_approval", task_id, user_id, correlation_id, {
                            "step_id": step.id,
                            "action": step.title,
                            "target": str(step.arguments.get("target", "system")),
                            "risk": step.risk_level.value,
                            "reason": policy_dec.safe_explanation,
                        })
                        return TaskResultSummary(
                            outcome=TaskStatus.WAITING_APPROVAL.value,
                            summary=f"Execution paused: Step '{step.title}' requires human approval ({policy_dec.safe_explanation}).",
                            evidence=collected_evidence,
                            artifacts=collected_artifacts,
                            changes=applied_changes,
                            verification={"status": "pending_approval", "step_id": step.id},
                            limitations=["Awaiting approval before mutating actions."],
                        )

                    steps_to_dispatch.append(step)

                # G. Execute Steps (Parallel Reads / Serialized Writes) (Spec 23, 25)
                tasks_coros = [
                    self._execute_single_step(
                        step=s,
                        user_id=user_id,
                        project_id=project_id,
                        dry_run=dry_run,
                        cancellation_token=cancellation_token,
                        budget_enforcer=budget_enforcer,
                        session=None,
                    )
                    for s in steps_to_dispatch
                ]
                results = await asyncio.gather(*tasks_coros, return_exceptions=True)

                # H. Process Step Results
                any_step_failed = False
                for step, res in zip(steps_to_dispatch, results):
                    if isinstance(res, Exception):
                        step.status = StepStatus.FAILED
                        step.error = str(res)
                        any_step_failed = True
                    elif isinstance(res, dict) and res.get("status") == StepStatus.FAILED.value:
                        step.status = StepStatus.FAILED
                        step.error = res.get("error", "Unknown error")
                        any_step_failed = True
                    else:
                        step.status = StepStatus.COMPLETED
                        step.completed_at = datetime.now(UTC)
                        step.result_reference = res
                        completed_step_ids.add(step.id)
                        step_results[step.id] = res

                        # Collect evidence and artifacts (Spec 26, 144)
                        if isinstance(res, dict):
                            collected_evidence.extend(res.get("evidence", []))
                            collected_artifacts.extend(res.get("artifacts", []))
                            if step.risk_level in (TaskRiskLevel.WRITE, TaskRiskLevel.DESTRUCTIVE):
                                applied_changes.append({"step": step.title, "output": str(res.get("output"))[:200]})

                        await self._publish_event("task.step.completed", task_id, user_id, correlation_id, {
                            "step_id": step.id,
                            "sequence": step.sequence,
                            "completed_count": len(completed_step_ids),
                            "total_count": len(current_plan.steps),
                        })

                # I. Checkpoint Progress (Spec 38)
                ckpt_data = CheckpointService.serialize_state(
                    task_id=task_id,
                    status=current_status,
                    plan_version=current_plan.version,
                    completed_step_ids=list(completed_step_ids),
                    pending_step_ids=[s.id for s in current_plan.steps if s.id not in completed_step_ids],
                    budget=budget_enforcer.current_budget,
                    artifacts=collected_artifacts,
                    step_results=step_results,
                )
                await CheckpointService.save_checkpoint(
                    session=session,
                    task_id=task_id,
                    plan_version=current_plan.version,
                    step_index=len(completed_step_ids),
                    state_data=ckpt_data,
                )

                # J. Handle Failures & Replanning (Spec 34, 35)
                if any_step_failed:
                    failed_steps = [s for s in steps_to_dispatch if s.status == StepStatus.FAILED]
                    failed_step = failed_steps[0]
                    classification = self.replanner.classify_failure(failed_step.error or "")

                    # Check automatic retry eligibility (Spec 32, 33)
                    can_retry, backoff = self.replanner.should_retry_step(failed_step, classification)
                    if can_retry:
                        failed_step.retry_count += 1
                        failed_step.status = StepStatus.READY
                        logger.info("Retrying step %s after %.1fs backoff", failed_step.id, backoff)
                        await asyncio.sleep(min(backoff, 2.0))  # Capped for responsive execution
                        continue

                    # Trigger Replanning (Spec 34, 35)
                    budget_enforcer.record_replan(1)
                    current_status = TaskStatus.REPLANNING
                    await self._publish_event("task.replanned", task_id, user_id, correlation_id, {
                        "failed_step": failed_step.id,
                        "classification": classification.value,
                    })

                    try:
                        current_plan = self.replanner.generate_alternative_step_plan(
                            current_plan=current_plan,
                            failed_step=failed_step,
                        )
                        current_status = TaskStatus.RUNNING
                    except LoopDetectedError as loop_err:
                        current_status = TaskStatus.FAILED
                        logger.warning("Terminating task %s due to loop: %s", task_id, loop_err)
                        break

        except (TaskCancelledError, asyncio.CancelledError):
            current_status = TaskStatus.CANCELLED
            await self._publish_event("task.cancelled", task_id, user_id, correlation_id, {})
        except EmergencyStopActiveError:
            current_status = TaskStatus.BLOCKED
            await self._publish_event("task.blocked", task_id, user_id, correlation_id, {"reason": "Emergency Stop"})
        except BudgetExceededError as be:
            current_status = TaskStatus.FAILED
            await self._publish_event("task.failed", task_id, user_id, correlation_id, {"reason": str(be)})
        except Exception as e:
            current_status = TaskStatus.FAILED
            logger.error("Unhandled engine error in task %s: %s", task_id, e)
            await self._publish_event("task.failed", task_id, user_id, correlation_id, {"error": str(e)})
        finally:
            # Cleanup scheduler fairness and locks (Spec 128, 131)
            self.scheduler.unregister_active_task(task_id, user_id, project_id)
            await self.scheduler.release_all_task_locks(task_id)
            self.cancellation_manager.remove_token(task_id)

        # Build final verifiable task summary (Spec 89, 147)
        outcome_str = current_status.value
        summary_text = (
            f"Task '{objective[:80]}' concluded with status {outcome_str}. "
            f"Executed {len(completed_step_ids)}/{len(current_plan.steps) if 'current_plan' in locals() else 0} steps."
        )

        final_summary = TaskResultSummary(
            outcome=outcome_str,
            summary=summary_text,
            evidence=collected_evidence,
            artifacts=collected_artifacts,
            changes=applied_changes,
            verification={"status": outcome_str, "steps_completed": len(completed_step_ids)},
            limitations=["Dry run simulation applied; no external mutations executed."] if dry_run else [],
        )

        await self._publish_event(
            "task.completed" if current_status == TaskStatus.COMPLETED else "task.failed",
            task_id,
            user_id,
            correlation_id,
            final_summary.model_dump(),
        )

        return final_summary

    async def _execute_single_step(
        self,
        step: TaskStepSchema,
        user_id: str,
        project_id: str | None,
        dry_run: bool,
        cancellation_token: CancellationToken,
        budget_enforcer: TaskBudgetEnforcer,
        session: AsyncSession | None,
    ) -> dict[str, Any]:
        """Dispatch a single step with budget and lock acquisition."""
        step.status = StepStatus.RUNNING
        step.started_at = datetime.now(UTC)

        # Acquire resource locks for write steps (Spec 56, 131)
        for res in step.resources:
            if res.mode.upper() == "WRITE":
                await self.scheduler.acquire_resource_lock(
                    resource_type=res.type.value if hasattr(res.type, "value") else str(res.type),
                    resource_id=res.id,
                    task_id=step.task_id,
                    user_id=user_id,
                    ttl_seconds=300,
                    session=session,
                )

        try:
            # Dry run simulation check (Spec 117)
            if dry_run and step.risk_level in (TaskRiskLevel.WRITE, TaskRiskLevel.DESTRUCTIVE):
                budget_enforcer.record_step(1)
                return {
                    "status": StepStatus.COMPLETED.value,
                    "output": f"[DRY_RUN] Simulated write action for '{step.title}' without applying changes.",
                    "evidence": [{"dry_run": True, "target": str(step.arguments)}],
                    "artifacts": [],
                    "exit_code": 0,
                    "duration_seconds": 0.05,
                }

            # Dispatch step via executor
            res = await self.executor.execute_step(
                step=step,
                user_id=user_id,
                project_id=project_id,
                cancellation_token=cancellation_token,
                session=session,
            )

            # Record budget consumption
            budget_enforcer.record_step(1)
            if step.tool_name:
                budget_enforcer.record_tool_calls(1)
            if step.skill_id:
                budget_enforcer.record_agent_call(1)

            # Track tool repetition for oscillation checks
            if step.tool_name:
                self.replanner.record_tool_execution(step.task_id, step.id, step.tool_name)

            return res
        finally:
            # Release resource locks
            for res in step.resources:
                if res.mode.upper() == "WRITE":
                    await self.scheduler.release_resource_lock(
                        resource_type=res.type.value if hasattr(res.type, "value") else str(res.type),
                        resource_id=res.id,
                        task_id=step.task_id,
                        session=session,
                    )

    async def _publish_event(
        self,
        event_type: str,
        task_id: str,
        user_id: str,
        correlation_id: str,
        payload: dict[str, Any],
    ) -> None:
        """Publish task events to the unified Event Bus (Spec 68)."""
        try:
            if self.event_bus:
                evt = Event(
                    event_type=event_type,
                    source=EventSource.TASK,
                    user_id=user_id,
                    correlation_id=correlation_id,
                    payload={"task_id": task_id, **payload},
                )
                await self.event_bus.publish(evt)
        except Exception as ex:
            logger.warning("Failed to publish task event %s: %s", event_type, ex)
