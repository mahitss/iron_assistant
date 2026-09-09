"""Distributed task execution leases with monotonic fencing tokens and heartbeats."""

from datetime import UTC, datetime, timedelta
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.resilience.models import TaskLeaseModel
from app.resilience.schemas import TaskLease, utc_now

logger = logging.getLogger(__name__)


class LeaseLostError(Exception):
    """Raised when a worker has lost its lease or fencing token is superseded."""
    pass


class LeaseManager:
    """Manages task execution leases, fencing tokens, and heartbeats."""

    def __init__(self, default_lease_ttl_seconds: int = 30) -> None:
        self.default_lease_ttl = default_lease_ttl_seconds
        self._memory_leases: dict[str, TaskLease] = {}

    async def acquire_lease(
        self,
        task_id: str,
        worker_id: str,
        ttl_seconds: int | None = None,
        session: AsyncSession | None = None,
    ) -> TaskLease:
        """Acquires or takes over an expired lease for a task, incrementing the fencing token."""
        ttl = ttl_seconds or self.default_lease_ttl
        now = utc_now()
        expires_at = now + timedelta(seconds=ttl)

        existing_fencing = 0
        existing = self._memory_leases.get(task_id)

        if session:
            try:
                stmt = select(TaskLeaseModel).where(TaskLeaseModel.task_id == task_id)
                res = await session.execute(stmt)
                db_lease = res.scalar_one_or_none()
                if db_lease:
                    db_expires = db_lease.expires_at.replace(tzinfo=UTC) if db_lease.expires_at.tzinfo is None else db_lease.expires_at
                    # Check if lease is active and held by another worker
                    if db_expires > now and db_lease.worker_id != worker_id:
                        raise LeaseLostError(
                            f"Task '{task_id}' is actively leased by worker '{db_lease.worker_id}' until {db_expires}."
                        )
                    existing_fencing = db_lease.fencing_token
                    # Overwrite or extend lease
                    db_lease.worker_id = worker_id
                    db_lease.fencing_token = existing_fencing + 1
                    db_lease.acquired_at = now
                    db_lease.expires_at = expires_at
                    db_lease.heartbeat_at = now
                    await session.commit()

                    lease = TaskLease.model_validate(db_lease)
                    self._memory_leases[task_id] = lease
                    return lease
                else:
                    new_db_lease = TaskLeaseModel(
                        task_id=task_id,
                        worker_id=worker_id,
                        fencing_token=1,
                        acquired_at=now,
                        expires_at=expires_at,
                        heartbeat_at=now,
                    )
                    session.add(new_db_lease)
                    await session.commit()

                    lease = TaskLease.model_validate(new_db_lease)
                    self._memory_leases[task_id] = lease
                    return lease
            except LeaseLostError:
                raise
            except Exception as e:
                logger.warning("Resilience: DB error acquiring lease for %s: %s", task_id, e)

        # Fallback to in-memory lease checking
        if existing:
            if existing.expires_at > now and existing.worker_id != worker_id:
                raise LeaseLostError(
                    f"Task '{task_id}' is actively leased by worker '{existing.worker_id}' until {existing.expires_at}."
                )
            existing_fencing = existing.fencing_token

        new_lease = TaskLease(
            task_id=task_id,
            worker_id=worker_id,
            fencing_token=existing_fencing + 1,
            acquired_at=now,
            expires_at=expires_at,
            heartbeat_at=now,
        )
        self._memory_leases[task_id] = new_lease
        return new_lease

    async def heartbeat(
        self,
        task_id: str,
        worker_id: str,
        fencing_token: int,
        extend_seconds: int | None = None,
        session: AsyncSession | None = None,
    ) -> bool:
        """Lightweight heartbeat to extend lease if fencing token still matches."""
        now = utc_now()
        ttl = extend_seconds or self.default_lease_ttl
        new_expires = now + timedelta(seconds=ttl)

        if session:
            try:
                stmt = select(TaskLeaseModel).where(TaskLeaseModel.task_id == task_id)
                res = await session.execute(stmt)
                db_lease = res.scalar_one_or_none()
                if not db_lease or db_lease.worker_id != worker_id or db_lease.fencing_token != fencing_token:
                    logger.warning("Resilience: Heartbeat rejected for %s: lease lost or superseded", task_id)
                    return False
                db_lease.heartbeat_at = now
                db_lease.expires_at = new_expires
                await session.commit()
            except Exception as e:
                logger.warning("Resilience: DB error during heartbeat for %s: %s", task_id, e)

        mem_lease = self._memory_leases.get(task_id)
        if mem_lease and mem_lease.worker_id == worker_id and mem_lease.fencing_token == fencing_token:
            mem_lease.heartbeat_at = now
            mem_lease.expires_at = new_expires
            return True

        return False

    async def release_lease(
        self,
        task_id: str,
        worker_id: str,
        session: AsyncSession | None = None,
    ) -> None:
        """Voluntarily releases a task lease (e.g. on graceful completion or shutdown)."""
        if session:
            try:
                stmt = select(TaskLeaseModel).where(
                    TaskLeaseModel.task_id == task_id,
                    TaskLeaseModel.worker_id == worker_id,
                )
                res = await session.execute(stmt)
                db_lease = res.scalar_one_or_none()
                if db_lease:
                    await session.delete(db_lease)
                    await session.commit()
            except Exception as e:
                logger.warning("Resilience: DB error releasing lease for %s: %s", task_id, e)

        mem_lease = self._memory_leases.get(task_id)
        if mem_lease and mem_lease.worker_id == worker_id:
            self._memory_leases.pop(task_id, None)

    async def validate_fencing_token(
        self,
        task_id: str,
        worker_id: str,
        fencing_token: int,
        session: AsyncSession | None = None,
    ) -> bool:
        """Validates that this worker still holds the current active lease and valid fencing token."""
        now = utc_now()
        if session:
            try:
                stmt = select(TaskLeaseModel).where(TaskLeaseModel.task_id == task_id)
                res = await session.execute(stmt)
                db_lease = res.scalar_one_or_none()
                if db_lease:
                    db_expires = db_lease.expires_at.replace(tzinfo=UTC) if db_lease.expires_at.tzinfo is None else db_lease.expires_at
                    return (
                        db_lease.worker_id == worker_id
                        and db_lease.fencing_token == fencing_token
                        and db_expires > now
                    )
            except Exception as e:
                logger.warning("Resilience: DB error validating fencing token for %s: %s", task_id, e)

        mem_lease = self._memory_leases.get(task_id)
        if mem_lease:
            return (
                mem_lease.worker_id == worker_id
                and mem_lease.fencing_token == fencing_token
                and mem_lease.expires_at > now
            )
        return False
