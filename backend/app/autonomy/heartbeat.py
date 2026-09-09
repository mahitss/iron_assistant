"""Heartbeat Emission and Worker Liveness Monitoring (Task 45)."""

from __future__ import annotations

from datetime import datetime, timezone
import logging
from typing import Dict, Optional

logger = logging.getLogger("kairo.autonomy.heartbeat")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class HeartbeatTracker:
    """Tracks active heartbeats emitted by running autonomous workers (Spec 24)."""

    def __init__(self, stale_threshold_seconds: int = 45) -> None:
        self.stale_threshold_seconds = stale_threshold_seconds
        # run_id -> (worker_id, last_heartbeat)
        self._heartbeats: Dict[str, tuple[str, datetime]] = {}

    def record_heartbeat(self, run_id: str, worker_id: str) -> datetime:
        now = utc_now()
        self._heartbeats[run_id] = (worker_id, now)
        return now

    def get_last_heartbeat(self, run_id: str) -> Optional[datetime]:
        entry = self._heartbeats.get(run_id)
        return entry[1] if entry else None

    def is_worker_alive(self, run_id: str) -> bool:
        """Check if worker has emitted a heartbeat within freshness window."""
        entry = self._heartbeats.get(run_id)
        if not entry:
            return False
        diff = (utc_now() - entry[1]).total_seconds()
        return diff <= self.stale_threshold_seconds

    def remove_run(self, run_id: str) -> None:
        self._heartbeats.pop(run_id, None)
