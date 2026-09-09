"""Distributed Execution Leases and Split-Brain Prevention (Task 45)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import logging
from typing import Any, Dict, Optional
import uuid

logger = logging.getLogger("kairo.autonomy.leases")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SplitBrainConflictError(Exception):
    """Raised when two workers attempt concurrent execution of the same run."""


@dataclass
class ExecutionLease:
    """Exclusive distributed lease guarding an active autonomous run (Spec 20, 21)."""

    lease_id: str
    run_id: str
    worker_id: str
    ttl_seconds: int = 30
    acquired_at: datetime = field(default_factory=utc_now)
    expires_at: datetime = field(default_factory=lambda: utc_now() + timedelta(seconds=30))

    @property
    def is_expired(self) -> bool:
        return utc_now() >= self.expires_at

    def renew(self, extension_seconds: int = 30) -> None:
        self.expires_at = utc_now() + timedelta(seconds=extension_seconds)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "lease_id": self.lease_id,
            "run_id": self.run_id,
            "worker_id": self.worker_id,
            "ttl_seconds": self.ttl_seconds,
            "acquired_at": self.acquired_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "is_expired": self.is_expired,
        }


class ExecutionLeaseManager:
    """Coordinates lease acquisition, renewal, and recovery without split-brain anomalies (Spec 21-23)."""

    def __init__(self, default_ttl_seconds: int = 30) -> None:
        self.default_ttl = default_ttl_seconds
        # run_id -> ExecutionLease
        self._leases: Dict[str, ExecutionLease] = {}

    def acquire_lease(self, run_id: str, worker_id: str, ttl_seconds: Optional[int] = None) -> ExecutionLease:
        """Acquire exclusive execution lease on a run. Prevents duplicate workers (Spec 21, 23)."""
        ttl = ttl_seconds or self.default_ttl
        now = utc_now()

        existing = self._leases.get(run_id)
        if existing and not existing.is_expired:
            if existing.worker_id != worker_id:
                logger.warning(
                    "Split-brain conflict on run %s: Worker '%s' attempted to acquire lease held by '%s'",
                    run_id,
                    worker_id,
                    existing.worker_id,
                )
                raise SplitBrainConflictError(
                    f"Run {run_id} is already leased to active worker '{existing.worker_id}' until {existing.expires_at}."
                )
            # Re-acquire/renew by same worker
            existing.renew(ttl)
            return existing

        lease_id = f"lease_{uuid.uuid4().hex[:10]}"
        lease = ExecutionLease(
            lease_id=lease_id,
            run_id=run_id,
            worker_id=worker_id,
            ttl_seconds=ttl,
            acquired_at=now,
            expires_at=now + timedelta(seconds=ttl),
        )
        self._leases[run_id] = lease
        logger.info("Worker '%s' acquired execution lease %s on run %s (TTL=%ds)", worker_id, lease_id, run_id, ttl)
        return lease

    def renew_lease(self, run_id: str, worker_id: str, extension_seconds: Optional[int] = None) -> bool:
        """Heartbeat renewal of active execution lease."""
        lease = self._leases.get(run_id)
        if not lease:
            return False
        if lease.worker_id != worker_id:
            logger.warning("Worker '%s' tried to renew lease held by '%s'", worker_id, lease.worker_id)
            return False
        lease.renew(extension_seconds or self.default_ttl)
        return True

    def release_lease(self, run_id: str, worker_id: str) -> bool:
        """Explicitly release execution lease upon completion, pause, or safe stop."""
        lease = self._leases.get(run_id)
        if not lease:
            return True
        if lease.worker_id != worker_id and not lease.is_expired:
            logger.warning("Unauthorized lease release attempt on run %s by worker '%s'", run_id, worker_id)
            return False
        del self._leases[run_id]
        logger.info("Worker '%s' released execution lease on run %s", worker_id, run_id)
        return True

    def get_lease(self, run_id: str) -> Optional[ExecutionLease]:
        return self._leases.get(run_id)
