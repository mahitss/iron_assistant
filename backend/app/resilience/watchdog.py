"""Watchdog for stuck task detection and quarantine management for poison tasks."""

from datetime import UTC, datetime, timedelta
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.resilience.models import QuarantineModel, TaskLeaseModel
from app.resilience.schemas import QuarantineRecord, RecoveryState, utc_now

logger = logging.getLogger(__name__)


class QuarantineManager:
    """Quarantines poison tasks that repeatedly crash or fail recovery loops."""

    MAX_RECOVERY_ATTEMPTS = 3

    def __init__(self) -> None:
        self._memory_quarantine: dict[str, QuarantineRecord] = {}

    async def is_quarantined(self, task_id: str, session: AsyncSession | None = None) -> bool:
        """Checks whether a task is currently quarantined."""
        if task_id in self._memory_quarantine:
            return self._memory_quarantine[task_id].status == "QUARANTINED"

        if session:
            try:
                stmt = select(QuarantineModel).where(
                    QuarantineModel.task_id == task_id,
                    QuarantineModel.status == "QUARANTINED",
                )
                res = await session.execute(stmt)
                return res.scalar_one_or_none() is not None
            except Exception as e:
                logger.warning("Resilience: DB error checking quarantine for %s: %s", task_id, e)

        return False

    async def quarantine_task(
        self,
        task_id: str,
        reason: str,
        quarantined_by: str | None = "WATCHDOG",
        session: AsyncSession | None = None,
    ) -> QuarantineRecord:
        """Quarantines a task to halt infinite restart/crash loops."""
        logger.warning("Resilience: Quarantining poison task '%s'. Reason: %s", task_id, reason)
        now = utc_now()

        rec = QuarantineRecord(
            task_id=task_id,
            reason=reason,
            failure_count=1,
            quarantined_by=quarantined_by,
            status="QUARANTINED",
            quarantined_at=now,
            released_at=None,
        )
        self._memory_quarantine[task_id] = rec

        if session:
            try:
                stmt = select(QuarantineModel).where(QuarantineModel.task_id == task_id)
                res = await session.execute(stmt)
                db_item = res.scalar_one_or_none()
                if db_item:
                    db_item.status = "QUARANTINED"
                    db_item.reason = reason
                    db_item.failure_count += 1
                    db_item.quarantined_at = now
                    db_item.released_at = None
                else:
                    db_item = QuarantineModel(
                        task_id=task_id,
                        reason=reason,
                        failure_count=1,
                        quarantined_by=quarantined_by,
                        status="QUARANTINED",
                        quarantined_at=now,
                        released_at=None,
                    )
                    session.add(db_item)
                await session.commit()
            except Exception as e:
                logger.warning("Resilience: DB error quarantining task %s: %s", task_id, e)

        return rec

    async def release_task(
        self,
        task_id: str,
        released_by: str | None = "OPERATOR",
        session: AsyncSession | None = None,
    ) -> bool:
        """Releases a task from quarantine so it may be inspected or resumed."""
        logger.info("Resilience: Task '%s' released from quarantine by %s", task_id, released_by)
        if task_id in self._memory_quarantine:
            self._memory_quarantine[task_id].status = "RELEASED"
            self._memory_quarantine[task_id].released_at = utc_now()

        if session:
            try:
                stmt = select(QuarantineModel).where(QuarantineModel.task_id == task_id)
                res = await session.execute(stmt)
                db_item = res.scalar_one_or_none()
                if db_item:
                    db_item.status = "RELEASED"
                    db_item.released_at = utc_now()
                    await session.commit()
                    return True
            except Exception as e:
                logger.warning("Resilience: DB error releasing task %s: %s", task_id, e)

        return task_id in self._memory_quarantine

    async def list_quarantined(self, session: AsyncSession | None = None) -> list[QuarantineRecord]:
        """Lists all active quarantined tasks."""
        if session:
            try:
                stmt = select(QuarantineModel).where(QuarantineModel.status == "QUARANTINED")
                res = await session.execute(stmt)
                return [QuarantineRecord.model_validate(m) for m in res.scalars().all()]
            except Exception as e:
                logger.warning("Resilience: DB error listing quarantined tasks: %s", e)

        return [rec for rec in self._memory_quarantine.values() if rec.status == "QUARANTINED"]


class TaskWatchdog:
    """Monitors running tasks for missing heartbeats and expired leases."""

    def __init__(self, quarantine_mgr: QuarantineManager | None = None) -> None:
        self.quarantine_mgr = quarantine_mgr or QuarantineManager()
        self.stuck_tasks_detected: int = 0
        self._recovery_counts: dict[str, int] = {}

    async def scan_for_stuck_tasks(
        self,
        stale_threshold_seconds: int = 60,
        session: AsyncSession | None = None,
    ) -> list[str]:
        """Identifies tasks whose lease expired or whose heartbeat ceased."""
        stuck_tasks: list[str] = []
        cutoff = utc_now() - timedelta(seconds=stale_threshold_seconds)

        if session:
            try:
                stmt = select(TaskLeaseModel).where(TaskLeaseModel.heartbeat_at < cutoff)
                res = await session.execute(stmt)
                stale_leases = res.scalars().all()
                for lease in stale_leases:
                    stuck_tasks.append(lease.task_id)
            except Exception as e:
                logger.warning("Resilience: DB error scanning stale leases: %s", e)

        for task_id in stuck_tasks:
            self.stuck_tasks_detected += 1
            rec_count = self._recovery_counts.get(task_id, 0) + 1
            self._recovery_counts[task_id] = rec_count

            if rec_count >= self.quarantine_mgr.MAX_RECOVERY_ATTEMPTS:
                await self.quarantine_mgr.quarantine_task(
                    task_id=task_id,
                    reason=f"Exceeded max recovery attempts ({rec_count}) after heartbeat loss.",
                    session=session,
                )

        return stuck_tasks
