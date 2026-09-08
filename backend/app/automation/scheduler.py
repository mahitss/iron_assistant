"""Scheduler service for polling due workflows and managing distributed execution locks."""

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.automation.idempotency import generate_scheduled_idempotency_key
from app.automation.models import Workflow, WorkflowRun
from app.automation.triggers import calculate_next_run
from app.core.config import Settings, get_settings

logger = logging.getLogger("kairo.automation.scheduler")


class SchedulerService:
    """Discovers and schedules due workflows while preventing duplicate concurrent runs."""

    def __init__(
        self,
        session_factory: Any = None,
        settings: Settings | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.settings = settings or get_settings()

    async def poll_due_workflows(self, session: AsyncSession) -> list[str]:
        """Find workflows due for execution, create their WorkflowRun, and advance next_run_at.

        Returns list of newly created run_ids.
        """
        now = datetime.now(UTC)

        # Select due enabled workflows
        stmt = select(Workflow).where(
            Workflow.enabled.is_(True),
            Workflow.next_run_at.is_not(None),
            Workflow.next_run_at <= now,
        )

        # Apply row-level locking if supported by dialect (PostgreSQL FOR UPDATE SKIP LOCKED)
        bind = session.bind
        if bind and bind.dialect.name == "postgresql":
            stmt = stmt.with_for_update(skip_locked=True)

        res = await session.execute(stmt)
        due_workflows = list(res.scalars().all())

        created_run_ids: list[str] = []

        for wf in due_workflows:
            scheduled_ts = wf.next_run_at or now
            idempotency_key = generate_scheduled_idempotency_key(wf.id, scheduled_ts)

            # Check if run with idempotency key already exists
            dup_stmt = select(WorkflowRun.id).where(WorkflowRun.idempotency_key == idempotency_key)
            dup_res = await session.execute(dup_stmt)
            if dup_res.scalar_one_or_none() is not None:
                logger.info(
                    "Run for workflow '%s' with key '%s' already exists; skipping duplicate.",
                    wf.id,
                    idempotency_key,
                )
            else:
                run_id = str(uuid.uuid4())
                run = WorkflowRun(
                    id=run_id,
                    workflow_id=wf.id,
                    user_id=wf.user_id,
                    status="pending",
                    idempotency_key=idempotency_key,
                    current_step=0,
                    created_at=now,
                    updated_at=now,
                )
                session.add(run)
                created_run_ids.append(run.id)

            # Advance next_run_at and update last_run_at
            wf.last_run_at = now
            wf.next_run_at = calculate_next_run(
                wf.trigger_config,
                from_time=now,
                min_interval_seconds=self.settings.KAIRO_MIN_SCHEDULE_INTERVAL_SECONDS,
            )
            # If next_run_at is None (e.g. interval='once'), disable workflow
            if wf.next_run_at is None:
                wf.enabled = False

        await session.commit()
        return created_run_ids

    async def recover_stale_runs(self, session: AsyncSession) -> int:
        """Identify runs stuck in 'running' state beyond timeout and mark them failed."""
        now = datetime.now(UTC)
        timeout_seconds = self.settings.KAIRO_WORKFLOW_TIMEOUT_SECONDS

        stmt = select(WorkflowRun).where(WorkflowRun.status == "running")
        res = await session.execute(stmt)
        running_runs = res.scalars().all()

        recovered_count = 0
        for run in running_runs:
            started = run.started_at or run.created_at
            if (now - started).total_seconds() > timeout_seconds:
                run.status = "failed"
                run.completed_at = now
                run.error = f"Workflow timed out after {timeout_seconds} seconds (stale run recovery)."
                recovered_count += 1

        if recovered_count > 0:
            await session.commit()
            logger.warning("Recovered %d stale workflow runs.", recovered_count)

        return recovered_count
