"""Attention Stack, Priority Queue, Fairness Aging & Hysteresis (Task 70).

Manages:
- Active focus
- LIFO Preemption Stack (cleanly resumes interrupted tasks with preserved state)
- Priority Queue (bounded attention)
- Fairness Aging (gradually elevates deferred low-priority tasks to prevent starvation)
- Hysteresis & Debounce (prevents rapid oscillation around threshold boundaries e.g. 79 <-> 81)
"""

from collections.abc import Sequence
from datetime import UTC, datetime

from app.attention.lifecycle import AttentionLifecycleStateMachine
from app.attention.schemas import AttentionCandidate, AttentionMode, AttentionState, AttentionThreshold


def utc_now() -> datetime:
    return datetime.now(UTC)


class AttentionStack:
    """Manages active focus, preemption stack, prioritized queue, aging, and hysteresis."""

    def __init__(self, mode: AttentionMode = AttentionMode.NORMAL_MODE):
        self.mode = mode
        self.current_focus: AttentionCandidate | None = None
        self.preempted_stack: list[AttentionCandidate] = []
        self.queue: list[AttentionCandidate] = []
        self.monitoring_pool: dict[str, AttentionCandidate] = {}
        self.deferred_pool: dict[str, AttentionCandidate] = {}

        # Hysteresis tracking: maps candidate_id -> last_stable_threshold
        self._threshold_cache: dict[str, AttentionThreshold] = {}

    def set_focus(self, candidate: AttentionCandidate) -> None:
        """Set candidate as active focus."""
        if self.current_focus and self.current_focus.attention_id != candidate.attention_id:
            # If replacing without preemption, current must be resolved or moved
            if self.current_focus.current_state == AttentionState.ATTENDING:
                AttentionLifecycleStateMachine.transition(
                    self.current_focus.current_state,
                    AttentionState.QUEUED,
                )
                self.current_focus.current_state = AttentionState.QUEUED
                self.queue.append(self.current_focus)

        if candidate.current_state != AttentionState.ATTENDING:
            candidate.current_state = AttentionLifecycleStateMachine.transition(
                candidate.current_state,
                AttentionState.ATTENDING,
            )

        self.current_focus = candidate
        # Remove from queue/deferred/monitoring if present
        self.queue = [c for c in self.queue if c.attention_id != candidate.attention_id]
        self.deferred_pool.pop(candidate.attention_id, None)
        self.monitoring_pool.pop(candidate.attention_id, None)

    def push_preemption(self, interrupted: AttentionCandidate, snapshot_id: str | None = None) -> None:
        """Push an interrupted candidate onto the preemption stack with preserved state."""
        interrupted.current_state = AttentionLifecycleStateMachine.transition(
            interrupted.current_state,
            AttentionState.PAUSED,
        )
        interrupted.interruption_count += 1
        if snapshot_id:
            interrupted.context_snapshot_id = snapshot_id

        self.preempted_stack.append(interrupted)
        if self.current_focus and self.current_focus.attention_id == interrupted.attention_id:
            self.current_focus = None

    def pop_resume(self) -> AttentionCandidate | None:
        """Pop the most recently preempted candidate and resume its active attention."""
        if not self.preempted_stack:
            return None

        resumed = self.preempted_stack.pop()
        resumed.current_state = AttentionLifecycleStateMachine.transition(
            resumed.current_state,
            AttentionState.ATTENDING,
        )
        self.current_focus = resumed
        return resumed

    def enqueue(self, candidate: AttentionCandidate) -> None:
        """Enqueue candidate into prioritized queue."""
        if candidate.current_state not in (AttentionState.QUEUED, AttentionState.BLOCKED):
            candidate.current_state = AttentionLifecycleStateMachine.transition(
                candidate.current_state,
                AttentionState.QUEUED,
            )

        # Remove existing instance if updating
        self.queue = [c for c in self.queue if c.attention_id != candidate.attention_id]
        self.queue.append(candidate)
        self._sort_queue()

    def dequeue_next(self) -> AttentionCandidate | None:
        """Dequeue highest priority candidate."""
        if not self.queue:
            return None
        self._sort_queue()
        return self.queue.pop(0)

    def defer(self, candidate: AttentionCandidate, reason: str = "") -> None:
        """Move candidate to deferred pool and track deferral count."""
        candidate.current_state = AttentionLifecycleStateMachine.transition(
            candidate.current_state,
            AttentionState.DEFERRED,
        )
        candidate.deferral_count += 1
        if reason:
            candidate.reason = reason

        self.deferred_pool[candidate.attention_id] = candidate
        self.queue = [c for c in self.queue if c.attention_id != candidate.attention_id]
        if self.current_focus and self.current_focus.attention_id == candidate.attention_id:
            self.current_focus = None

    def monitor(self, candidate: AttentionCandidate) -> None:
        """Move candidate to monitoring pool."""
        candidate.current_state = AttentionLifecycleStateMachine.transition(
            candidate.current_state,
            AttentionState.MONITORING,
        )
        self.monitoring_pool[candidate.attention_id] = candidate
        self.queue = [c for c in self.queue if c.attention_id != candidate.attention_id]
        if self.current_focus and self.current_focus.attention_id == candidate.attention_id:
            self.current_focus = None

    def apply_fairness_aging(self, boost_per_cycle: float = 0.03, max_boost: float = 0.25) -> list[str]:
        """Apply anti-starvation aging boost to queued and deferred candidates.

        Gradually increases scheduling priority of older tasks without overriding critical safety items.
        """
        escalated_ids: list[str] = []

        # Age deferred pool
        for cid, cand in list(self.deferred_pool.items()):
            cand.aging_boost = min(max_boost, cand.aging_boost + boost_per_cycle)
            cand.attention_score = min(1.0, cand.attention_score + boost_per_cycle)
            # If aged sufficiently and not blocked, re-queue
            if cand.aging_boost >= 0.12 and cand.current_state == AttentionState.DEFERRED:
                cand.current_state = AttentionLifecycleStateMachine.transition(
                    cand.current_state,
                    AttentionState.QUEUED,
                )
                self.deferred_pool.pop(cid, None)
                self.enqueue(cand)
                escalated_ids.append(cid)

        # Age queued items
        for cand in self.queue:
            cand.aging_boost = min(max_boost, cand.aging_boost + (boost_per_cycle * 0.5))
            cand.attention_score = min(1.0, cand.attention_score + (boost_per_cycle * 0.5))

        self._sort_queue()
        return escalated_ids

    def check_hysteresis(
        self,
        candidate_id: str,
        current_threshold: AttentionThreshold,
        new_score: float,
        margin: float = 0.04,
    ) -> AttentionThreshold:
        """Prevent rapid threshold thrashing (e.g. 79 <-> 81) using band margins."""
        # Threshold boundary targets
        # LOW: 0.20, NORMAL: 0.40, HIGH: 0.70, CRITICAL: 0.85
        threshold_floors = {
            AttentionThreshold.IGNORE: 0.0,
            AttentionThreshold.LOW: 0.20,
            AttentionThreshold.NORMAL: 0.40,
            AttentionThreshold.HIGH: 0.70,
            AttentionThreshold.CRITICAL: 0.85,
        }

        # If previously stable, require crossing boundary + margin to change
        last_threshold = self._threshold_cache.get(candidate_id, current_threshold)

        if last_threshold == AttentionThreshold.HIGH:
            # To drop from HIGH to NORMAL, score must fall below 0.70 - margin (0.66)
            if new_score < (threshold_floors[AttentionThreshold.HIGH] - margin):
                effective = AttentionThreshold.NORMAL
            elif new_score >= threshold_floors[AttentionThreshold.CRITICAL] + margin:
                effective = AttentionThreshold.CRITICAL
            else:
                effective = AttentionThreshold.HIGH

        elif last_threshold == AttentionThreshold.NORMAL:
            # To escalate from NORMAL to HIGH, score must exceed 0.70 + margin (0.74)
            if new_score >= (threshold_floors[AttentionThreshold.HIGH] + margin):
                effective = AttentionThreshold.HIGH
            elif new_score < (threshold_floors[AttentionThreshold.NORMAL] - margin):
                effective = AttentionThreshold.LOW
            else:
                effective = AttentionThreshold.NORMAL
        else:
            effective = current_threshold

        self._threshold_cache[candidate_id] = effective
        return effective

    def _sort_queue(self) -> None:
        """Sort priority queue: highest attention score first."""
        self.queue.sort(key=lambda c: (c.attention_score, c.urgency), reverse=True)

    def get_all_active(self) -> Sequence[AttentionCandidate]:
        """Return all active items across focus, stack, queue, monitoring, and deferred."""
        items: list[AttentionCandidate] = []
        if self.current_focus:
            items.append(self.current_focus)
        items.extend(self.preempted_stack)
        items.extend(self.queue)
        items.extend(self.monitoring_pool.values())
        items.extend(self.deferred_pool.values())
        return items
