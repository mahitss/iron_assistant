"""Workflow run executor managing step execution, conditions, approvals, and retries."""

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.automation.actions import WorkflowActionRunner
from app.automation.approvals import create_approval_request
from app.automation.conditions import ConditionEngine
from app.automation.models import (
    ApprovalRequest,
    Notification,
    Workflow,
    WorkflowEvent,
    WorkflowRun,
    WorkflowStep,
)
from app.automation.retry import RetryPolicy
from app.automation.state import (
    WorkflowStatus,
    is_terminal_state,
    transition_state,
)
from app.core.config import Settings, get_settings

logger = logging.getLogger("kairo.automation.executor")


class WorkflowExecutor:
    """Orchestrates step-by-step execution of a WorkflowRun."""

    def __init__(
        self,
        session: AsyncSession,
        action_runner: WorkflowActionRunner | None = None,
        retry_policy: RetryPolicy | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.session = session
        self.action_runner = action_runner or WorkflowActionRunner()
        self.retry_policy = retry_policy or RetryPolicy()
        self.settings = settings or get_settings()

    async def execute_run(self, run_id: str) -> WorkflowRun:
        """Execute or resume a WorkflowRun."""
        stmt = select(WorkflowRun).where(WorkflowRun.id == run_id)
        result = await self.session.execute(stmt)
        run = result.scalar_one_or_none()
        if not run:
            raise ValueError(f"WorkflowRun '{run_id}' not found.")

        if is_terminal_state(run.status):
            logger.info("WorkflowRun '%s' is already in terminal state '%s'.", run_id, run.status)
            return run

        # Load parent workflow
        wf_stmt = select(Workflow).where(Workflow.id == run.workflow_id)
        wf_res = await self.session.execute(wf_stmt)
        workflow = wf_res.scalar_one_or_none()
        if not workflow:
            run.status = transition_state(run.status, WorkflowStatus.FAILED).value
            run.error = "Parent workflow not found"
            await self.session.commit()
            return run

        # Transition to RUNNING if pending or retrying
        if run.status in (WorkflowStatus.PENDING.value, WorkflowStatus.RETRYING.value):
            run.status = transition_state(run.status, WorkflowStatus.RUNNING).value
            run.started_at = run.started_at or datetime.now(UTC)
            await self._emit_event(run.id, workflow.id, "workflow.started", {})
            await self.session.commit()

        # Load or initialize steps
        steps_stmt = (
            select(WorkflowStep).where(WorkflowStep.run_id == run.id).order_by(WorkflowStep.step_index)
        )
        steps_res = await self.session.execute(steps_stmt)
        steps = list(steps_res.scalars().all())

        if not steps:
            steps = await self._initialize_steps(run, workflow)

        # Context holds outputs of previously completed steps: e.g. context["step_0"] = {...}
        context: dict[str, Any] = {"workflow_id": workflow.id, "run_id": run.id}
        for s in steps:
            if s.status == "completed" and s.result_summary:
                context[f"step_{s.step_index}"] = s.result_summary
                context["last_result"] = s.result_summary

        # Execute remaining steps sequentially
        for step in steps[run.current_step :]:
            if run.status != WorkflowStatus.RUNNING.value:
                break

            step_success = await self._execute_step(run, step, context)
            if not step_success:
                # Check if paused for approval
                if run.status == WorkflowStatus.WAITING_APPROVAL.value:
                    logger.info("WorkflowRun '%s' paused at step %d for approval.", run.id, step.step_index)
                    return run
                # Check if completed early (e.g. condition stopped)
                if run.status == WorkflowStatus.COMPLETED.value:
                    run.completed_at = datetime.now(UTC)
                    await self._emit_event(
                        run.id, workflow.id, "workflow.completed", {"stopped_at_step": step.step_index}
                    )
                    await self.session.commit()
                    return run
                # Otherwise failure
                run.status = transition_state(run.status, WorkflowStatus.FAILED).value
                run.completed_at = datetime.now(UTC)
                run.error = step.error or f"Step {step.step_index} failed"
                await self._emit_event(run.id, workflow.id, "workflow.failed", {"error": run.error})
                await self.session.commit()
                return run

            run.current_step = step.step_index + 1
            await self.session.commit()

        # If all steps finished successfully
        if run.status == WorkflowStatus.RUNNING.value:
            run.status = transition_state(run.status, WorkflowStatus.COMPLETED).value
            run.completed_at = datetime.now(UTC)
            await self._emit_event(run.id, workflow.id, "workflow.completed", {})
            await self.session.commit()

        return run

    async def _initialize_steps(self, run: WorkflowRun, workflow: Workflow) -> list[WorkflowStep]:
        """Create initial step rows from workflow.action_config."""
        steps_conf = workflow.action_config.get("steps", [])
        created_steps = []
        for idx, sc in enumerate(steps_conf):
            step = WorkflowStep(
                run_id=run.id,
                step_index=idx,
                step_type=sc.get("type", "action"),
                configuration=sc.get("config", {}),
                status="pending",
                attempt_count=0,
            )
            self.session.add(step)
            created_steps.append(step)
        await self.session.commit()
        return created_steps

    async def _execute_step(
        self,
        run: WorkflowRun,
        step: WorkflowStep,
        context: dict[str, Any],
    ) -> bool:
        """Execute a single workflow step."""
        step.status = "running"
        step.started_at = step.started_at or datetime.now(UTC)
        step.attempt_count += 1
        await self._emit_event(
            run.id, run.workflow_id, "workflow.step_started", {"step_index": step.step_index}
        )

        step_type = step.step_type

        try:
            if step_type == "action":
                tool_name = step.configuration.get("tool", "")
                arguments = step.configuration.get("arguments", {})
                # Resolve any dynamic variables from context if needed
                resolved_args = self._resolve_arguments(arguments, context)

                # Check if approval already granted for this step
                is_approved = await self._is_step_approved(run.id, step.id)

                action_res = await self.action_runner.execute_action(
                    tool_name=tool_name,
                    arguments=resolved_args,
                    is_approved=is_approved,
                )

                if action_res.requires_approval:
                    # Create ApprovalRequest and pause run
                    approval = create_approval_request(
                        user_id=run.user_id,
                        run_id=run.id,
                        step_id=step.id,
                        tool_name=tool_name,
                        tool_args=resolved_args,
                        permission_level=action_res.permission_level.value
                        if action_res.permission_level
                        else "EXTERNAL",
                        timeout_seconds=self.settings.KAIRO_APPROVAL_TIMEOUT_SECONDS,
                    )
                    self.session.add(approval)
                    run.status = transition_state(run.status, WorkflowStatus.WAITING_APPROVAL).value
                    await self._emit_event(
                        run.id,
                        run.workflow_id,
                        "workflow.approval_required",
                        {"tool": tool_name, "approval_id": approval.id},
                    )
                    await self.session.commit()
                    return False

                if not action_res.success:
                    step.status = "failed"
                    step.error = action_res.error or "Tool execution failed"
                    return False

                step.status = "completed"
                step.completed_at = datetime.now(UTC)
                step.result_summary = {"result": action_res.result}
                context[f"step_{step.step_index}"] = step.result_summary
                context["last_result"] = step.result_summary
                await self._emit_event(
                    run.id, run.workflow_id, "workflow.step_completed", {"step_index": step.step_index}
                )
                return True

            elif step_type == "condition":
                condition_def = step.configuration
                eval_data = context.get("last_result", {})
                passed = ConditionEngine.evaluate(condition_def, eval_data)
                step.status = "completed"
                step.completed_at = datetime.now(UTC)
                step.result_summary = {"condition_passed": passed}
                context[f"step_{step.step_index}"] = step.result_summary
                context["last_result"] = step.result_summary
                await self._emit_event(
                    run.id,
                    run.workflow_id,
                    "workflow.step_completed",
                    {"step_index": step.step_index, "passed": passed},
                )
                # If condition false and on_false="stop", stop workflow cleanly
                if not passed and step.configuration.get("on_false") == "stop":
                    run.status = transition_state(run.status, WorkflowStatus.COMPLETED).value
                    return False
                return True

            elif step_type == "notification":
                title = step.configuration.get("title", "Kairo Notification")
                msg = step.configuration.get("message", "")
                level = step.configuration.get("level", "info")

                notif = Notification(
                    user_id=run.user_id,
                    workflow_id=run.workflow_id,
                    run_id=run.id,
                    title=title,
                    message=msg,
                    level=level,
                    read=False,
                )
                self.session.add(notif)
                step.status = "completed"
                step.completed_at = datetime.now(UTC)
                step.result_summary = {"notified": True, "title": title}
                return True

            else:
                step.status = "failed"
                step.error = f"Unsupported step type: '{step_type}'"
                return False

        except Exception as exc:
            step.status = "failed"
            step.error = str(exc)
            logger.error("Error executing step %d of run '%s': %s", step.step_index, run.id, exc)
            return False

    async def _is_step_approved(self, run_id: str, step_id: str | None) -> bool:
        """Check if approval was granted for this step."""
        if not step_id:
            return False
        stmt = select(ApprovalRequest).where(
            ApprovalRequest.run_id == run_id,
            ApprovalRequest.step_id == step_id,
            ApprovalRequest.status == "approved",
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none() is not None

    def _resolve_arguments(self, args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        """Optionally substitute variables from step outputs into arguments."""
        resolved = {}
        for k, v in args.items():
            if isinstance(v, str) and v.startswith("{{") and v.endswith("}}"):
                var_name = v[2:-2].strip()
                resolved[k] = ConditionEngine.resolve_field(context, var_name)
            else:
                resolved[k] = v
        return resolved

    async def _emit_event(
        self,
        run_id: str | None,
        workflow_id: str | None,
        event_type: str,
        payload: dict[str, Any],
    ) -> None:
        """Persist a workflow audit event."""
        event = WorkflowEvent(
            run_id=run_id,
            workflow_id=workflow_id,
            event_type=event_type,
            payload=payload,
            created_at=datetime.now(UTC),
        )
        self.session.add(event)
