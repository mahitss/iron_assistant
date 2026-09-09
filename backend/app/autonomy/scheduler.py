"""Autonomous Task Scheduler, Dependency DAG Resolver, and Event Correlation Engine (Task 45)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
from typing import Any, Callable, Dict, List, Optional, Set
import uuid

logger = logging.getLogger("kairo.autonomy.scheduler")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class EventAuthenticityError(Exception):
    """Raised when an external event fails cryptographic signature or tenant correlation check (Spec 105)."""


@dataclass
class CorrelatedEvent:
    """External or internal event correlated with an autonomous execution run (Spec 100, 101)."""

    event_id: str
    run_id: str
    step_id: Optional[str]
    event_type: str
    idempotency_key: Optional[str]
    sequence_num: int
    payload: Dict[str, Any] = field(default_factory=dict)
    is_authenticated: bool = True
    received_at: datetime = field(default_factory=utc_now)


class AutonomousScheduler:
    """Schedules step execution based on DAG dependencies and correlates asynchronous events (Spec 29-32, 98-105)."""

    def __init__(self, max_concurrent_steps: int = 4) -> None:
        self.max_concurrent_steps = max_concurrent_steps
        # run_id -> set of processed event_ids (for deduplication, Spec 102)
        self._processed_events: Dict[str, Set[str]] = {}
        # run_id -> highest sequence number observed (for out-of-order handling, Spec 103)
        self._last_observed_sequence: Dict[str, int] = {}
        # run_id -> dict of step_id to async task status
        self._async_polls: Dict[str, Dict[str, Dict[str, Any]]] = {}

    def get_ready_steps(
        self,
        steps: List[Dict[str, Any]],
        completed_step_ids: Set[str],
        in_progress_step_ids: Set[str],
    ) -> List[Dict[str, Any]]:
        """Identify all steps whose dependencies are satisfied and available for execution (Spec 29-31)."""
        available_slots = max(0, self.max_concurrent_steps - len(in_progress_step_ids))
        if available_slots == 0:
            return []

        ready: List[Dict[str, Any]] = []
        for s in steps:
            sid = s.get("step_id", s.get("id"))
            if sid in completed_step_ids or sid in in_progress_step_ids:
                continue

            deps = set(s.get("dependencies", []))
            if deps.issubset(completed_step_ids):
                ready.append(s)
                if len(ready) >= available_slots:
                    break

        return ready

    def process_incoming_event(
        self,
        run_id: str,
        event_id: str,
        event_type: str,
        sequence_num: int,
        step_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
        is_authenticated: bool = True,
    ) -> Optional[CorrelatedEvent]:
        """Validate, deduplicate, and sequence incoming external callbacks (Spec 101-105)."""
        # 1. Event authenticity check (Spec 105)
        if not is_authenticated:
            logger.error("Event %s failed authenticity verification. Rejecting.", event_id)
            raise EventAuthenticityError(f"Event {event_id} failed authenticity or cryptographic signature verification.")

        # 2. Duplicate event check (Spec 102)
        processed = self._processed_events.setdefault(run_id, set())
        if event_id in processed:
            logger.info("Ignoring duplicate event %s for run %s", event_id, run_id)
            return None

        # 3. Out-of-order / stale event check (Spec 103, 104)
        last_seq = self._last_observed_sequence.get(run_id, 0)
        if sequence_num < last_seq:
            logger.warning(
                "Stale event detected: Event %s sequence %d < last observed sequence %d. Archiving as stale.",
                event_id,
                sequence_num,
                last_seq,
            )
            processed.add(event_id)
            return None

        # Record event as processed
        processed.add(event_id)
        self._last_observed_sequence[run_id] = max(last_seq, sequence_num)

        correlated = CorrelatedEvent(
            event_id=event_id,
            run_id=run_id,
            step_id=step_id,
            event_type=event_type,
            idempotency_key=idempotency_key,
            sequence_num=sequence_num,
            payload=payload or {},
            is_authenticated=True,
        )
        logger.info("Successfully correlated authenticated event %s with run %s (step=%s)", event_id, run_id, step_id)
        return correlated

    def register_async_poll(
        self,
        run_id: str,
        step_id: str,
        poll_fn_name: str,
        max_timeout_seconds: float = 120.0,
    ) -> None:
        """Register an async polling requirement with bounded timeout (Spec 99)."""
        self._async_polls.setdefault(run_id, {})[step_id] = {
            "poll_fn_name": poll_fn_name,
            "max_timeout_seconds": max_timeout_seconds,
            "started_at": utc_now().isoformat(),
            "status": "POLLING",
        }

    def evaluate_poll_timeout(self, run_id: str, step_id: str, elapsed_seconds: float) -> bool:
        poll_info = self._async_polls.get(run_id, {}).get(step_id)
        if not poll_info:
            return False
        if elapsed_seconds >= poll_info["max_timeout_seconds"]:
            poll_info["status"] = "TIMEOUT"
            logger.warning("Async poll for run %s step %s timed out after %.1fs", run_id, step_id, elapsed_seconds)
            return True
        return False
