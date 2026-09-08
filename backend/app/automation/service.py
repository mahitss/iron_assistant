"""AutomationService orchestrating workflows, runs, approvals, and tenant security."""

import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.automation.approvals import apply_approval_decision
from app.automation.executor import WorkflowExecutor
from app.automation.idempotency import generate_manual_idempotency_key
from app.automation.models import (
    ApprovalRequest,
    Notification,
    Workflow,
    WorkflowRun,
)
from app.automation.safety import (
    AutomationSecurityError,
    sanitize_workflow_name,
    verify_user_ownership,
)
from app.automation.schemas import WorkflowCreate, WorkflowUpdate
from app.automation.state import (
    WorkflowStatus,
    transition_state,
)
from app.automation.triggers import calculate_next_run
from app.core.config import Settings, get_settings

logger = logging.getLogger("kairo.automation.service")


class AutomationService:
    """Core service for managing user-scoped workflows, runs, and approvals."""

    def __init__(
        self,
        session: AsyncSession,
        settings: Settings | None = None,
        executor: WorkflowExecutor | None = None,
    ) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.executor = executor or WorkflowExecutor(session=self.session, settings=self.settings)

    # --- Workflow CRUD ---

    async def create_workflow(self, user_id: str, data: WorkflowCreate) -> Workflow:
        """Create a new durable workflow definition scoped to user_id."""
        if not user_id or not user_id.strip():
            raise AutomationSecurityError("User ID cannot be empty.")

        # Rate limit check: max workflows per user
        count_stmt = select(Workflow.id).where(Workflow.user_id == user_id)
        count_res = await self.session.execute(count_stmt)
        existing_count = len(count_res.scalars().all())
        if existing_count >= self.settings.KAIRO_MAX_WORKFLOWS_PER_USER:
            raise AutomationSecurityError(
                f"Maximum workflow limit ({self.settings.KAIRO_MAX_WORKFLOWS_PER_USER}) reached for user."
            )

        trigger_dict = data.trigger.model_dump()
        now = datetime.now(UTC)
        next_run = None
        if data.enabled and trigger_dict.get("trigger_type") == "schedule":
            next_run = calculate_next_run(
                trigger_dict,
                from_time=now,
                min_interval_seconds=self.settings.KAIRO_MIN_SCHEDULE_INTERVAL_SECONDS,
            )

        workflow = Workflow(
            user_id=user_id,
            name=sanitize_workflow_name(data.name),
            description=data.description.strip(),
            enabled=data.enabled,
            trigger_type=trigger_dict.get("trigger_type", "manual"),
            trigger_config=trigger_dict,
            action_config=data.actions.model_dump(),
            created_at=now,
            updated_at=now,
            next_run_at=next_run,
            version=1,
        )
        self.session.add(workflow)
        await self.session.commit()
        await self.session.refresh(workflow)
        return workflow

    async def get_workflow(self, workflow_id: str, user_id: str) -> Workflow:
        """Fetch a specific workflow, enforcing tenant isolation."""
        stmt = select(Workflow).where(Workflow.id == workflow_id)
        res = await self.session.execute(stmt)
        wf = res.scalar_one_or_none()
        if not wf:
            raise FileNotFoundError(f"Workflow '{workflow_id}' not found.")
        verify_user_ownership(wf, user_id)
        return wf

    async def list_workflows(self, user_id: str) -> list[Workflow]:
        """List all workflows belonging to user_id."""
        stmt = select(Workflow).where(Workflow.user_id == user_id).order_by(Workflow.created_at.desc())
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def update_workflow(
        self,
        workflow_id: str,
        user_id: str,
        data: WorkflowUpdate,
    ) -> Workflow:
        """Update workflow configuration, enabling/disabling, or triggers."""
        wf = await self.get_workflow(workflow_id, user_id)

        now = datetime.now(UTC)
        if data.name is not None:
            wf.name = sanitize_workflow_name(data.name)
        if data.description is not None:
            wf.description = data.description.strip()
        if data.enabled is not None:
            wf.enabled = data.enabled
        if data.trigger is not None:
            wf.trigger_config = data.trigger.model_dump()
            wf.trigger_type = wf.trigger_config.get("trigger_type", "manual")
        if data.actions is not None:
            wf.action_config = data.actions.model_dump()

        # Recalculate schedule if needed
        if wf.enabled and wf.trigger_type == "schedule":
            wf.next_run_at = calculate_next_run(
                wf.trigger_config,
                from_time=now,
                min_interval_seconds=self.settings.KAIRO_MIN_SCHEDULE_INTERVAL_SECONDS,
            )
        else:
            wf.next_run_at = None

        wf.version += 1
        wf.updated_at = now
        await self.session.commit()
        await self.session.refresh(wf)
        return wf

    async def delete_workflow(self, workflow_id: str, user_id: str) -> bool:
        """Delete a workflow and cascade delete associated runs."""
        wf = await self.get_workflow(workflow_id, user_id)
        await self.session.delete(wf)
        await self.session.commit()
        return True

    # --- Manual Run & Execution ---

    async def run_workflow_manually(
        self,
        workflow_id: str,
        user_id: str,
        client_token: str | None = None,
    ) -> WorkflowRun:
        """Trigger an immediate execution of a workflow."""
        wf = await self.get_workflow(workflow_id, user_id)

        # Concurrency check: max active runs per user
        active_stmt = select(WorkflowRun.id).where(
            WorkflowRun.user_id == user_id,
            WorkflowRun.status.in_(["pending", "running", "waiting_approval"]),
        )
        active_res = await self.session.execute(active_stmt)
        active_count = len(active_res.scalars().all())
        if active_count >= self.settings.KAIRO_MAX_CONCURRENT_WORKFLOW_RUNS:
            raise AutomationSecurityError(
                f"Maximum concurrent runs ({self.settings.KAIRO_MAX_CONCURRENT_WORKFLOW_RUNS}) reached for user."
            )

        now = datetime.now(UTC)
        idempotency_key = generate_manual_idempotency_key(wf.id, client_token)

        run = WorkflowRun(
            workflow_id=wf.id,
            user_id=user_id,
            status="pending",
            idempotency_key=idempotency_key,
            current_step=0,
            created_at=now,
            updated_at=now,
        )
        self.session.add(run)
        wf.last_run_at = now
        await self.session.commit()
        await self.session.refresh(run)

        # Dispatch execution
        run = await self.executor.execute_run(run.id)
        return run

    async def get_workflow_run(self, run_id: str, user_id: str) -> WorkflowRun:
        """Fetch a specific run with eager-loaded steps and approvals."""
        stmt = (
            select(WorkflowRun)
            .where(WorkflowRun.id == run_id)
            .options(
                selectinload(WorkflowRun.steps),
                selectinload(WorkflowRun.approvals),
            )
        )
        res = await self.session.execute(stmt)
        run = res.scalar_one_or_none()
        if not run:
            raise FileNotFoundError(f"WorkflowRun '{run_id}' not found.")
        verify_user_ownership(run, user_id)
        return run

    async def list_workflow_runs(self, workflow_id: str, user_id: str) -> list[WorkflowRun]:
        """List all runs for a specific workflow."""
        await self.get_workflow(workflow_id, user_id)
        stmt = (
            select(WorkflowRun)
            .where(WorkflowRun.workflow_id == workflow_id)
            .order_by(WorkflowRun.created_at.desc())
            .options(
                selectinload(WorkflowRun.steps),
                selectinload(WorkflowRun.approvals),
            )
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def cancel_run(self, workflow_id: str, user_id: str) -> WorkflowRun:
        """Cancel an active or pending run for a workflow."""
        await self.get_workflow(workflow_id, user_id)
        stmt = (
            select(WorkflowRun)
            .where(
                WorkflowRun.workflow_id == workflow_id,
                WorkflowRun.status.in_(["pending", "running", "waiting_approval", "retrying"]),
            )
            .order_by(WorkflowRun.created_at.desc())
        )
        res = await self.session.execute(stmt)
        active_run = res.scalar_one_or_none()
        if not active_run:
            raise RuntimeError(f"No active run found for workflow '{workflow_id}' to cancel.")

        active_run.status = transition_state(active_run.status, WorkflowStatus.CANCELLED).value
        active_run.completed_at = datetime.now(UTC)
        await self.session.commit()
        await self.session.refresh(active_run)
        return active_run

    # --- Approvals ---

    async def list_pending_approvals(self, user_id: str) -> list[ApprovalRequest]:
        """List pending human-in-the-loop approval requests."""
        now = datetime.now(UTC)
        stmt = (
            select(ApprovalRequest)
            .where(
                ApprovalRequest.user_id == user_id,
                ApprovalRequest.status == "pending",
                ApprovalRequest.expires_at > now,
            )
            .order_by(ApprovalRequest.created_at.desc())
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def decide_approval(
        self,
        approval_id: str,
        user_id: str,
        decision: str,
        reason: str | None = None,
    ) -> ApprovalRequest:
        """Approve or deny a pending action and resume/fail the workflow run."""
        stmt = select(ApprovalRequest).where(ApprovalRequest.id == approval_id)
        res = await self.session.execute(stmt)
        approval = res.scalar_one_or_none()
        if not approval:
            raise FileNotFoundError(f"Approval request '{approval_id}' not found.")

        # Apply decision checks
        apply_approval_decision(approval, decision, user_id)
        await self.session.commit()

        # Update run status based on decision
        run_stmt = select(WorkflowRun).where(WorkflowRun.id == approval.run_id)
        run_res = await self.session.execute(run_stmt)
        run = run_res.scalar_one_or_none()

        if run and run.status == WorkflowStatus.WAITING_APPROVAL.value:
            if decision == "approve":
                # Resume execution
                run.status = transition_state(run.status, WorkflowStatus.RUNNING).value
                await self.session.commit()
                # Continue execution of remaining steps
                await self.executor.execute_run(run.id)
            else:
                run.status = transition_state(run.status, WorkflowStatus.FAILED).value
                run.completed_at = datetime.now(UTC)
                run.error = f"Approval denied by user: {reason or 'No reason provided'}"
                await self.session.commit()

        return approval

    # --- Notifications ---

    async def list_notifications(self, user_id: str) -> list[Notification]:
        """List notifications produced by user's workflows."""
        stmt = (
            select(Notification)
            .where(Notification.user_id == user_id)
            .order_by(Notification.created_at.desc())
            .limit(50)
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())
