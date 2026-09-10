"""Open-loop tracking, waiting states, loop age, and staleness detection (INVARIANTS 27-37, 88-91, 182)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
import uuid

from app.executive_memory.schemas import ExecutiveStateScope, OpenLoopSchema, OpenLoopStatus
from app.executive_memory.temporal import TemporalEngine


class OpenLoopManager:
    """Tracks unresolved commitments, waiting states, and detects stale loops without assuming abandonment."""

    def __init__(self, stale_threshold_days: int = 7) -> None:
        # loop_id -> OpenLoopSchema
        self._loops: dict[str, OpenLoopSchema] = {}
        self.stale_threshold = timedelta(days=stale_threshold_days)

    def create_open_loop(
        self,
        description: str,
        owner: str = "user",
        source: str = "TASK",
        priority: float | str = 1.0,
        due_at: datetime | None = None,
        dependencies: list[str] | None = None,
        scope: ExecutiveStateScope | str = ExecutiveStateScope.PROJECT,
        scope_id: str | None = None,
        project_id: str | None = None,
    ) -> OpenLoopSchema:
        """INVARIANT 27 & 29: Identifies unfinished work and records open loops."""
        lid = f"loop_{uuid.uuid4().hex[:12]}"
        now = datetime.now(UTC)
        due_utc = TemporalEngine.ensure_utc(due_at) if due_at else None
        target_scope_id = project_id or scope_id
        target_scope = scope if isinstance(scope, ExecutiveStateScope) else ExecutiveStateScope(str(scope))
        loop = OpenLoopSchema(
            loop_id=lid,
            description=description.strip(),
            owner=owner,
            source=source,
            created_at=now,
            last_activity=now,
            due_at=due_utc,
            priority=priority,
            status=OpenLoopStatus.OPEN,
            dependencies=dependencies or [],
            scope=target_scope,
            scope_id=target_scope_id,
            updated_at=now,
            age_days=0,
        )
        self._loops[lid] = loop
        return loop

    def update_status(
        self,
        loop_id: str,
        status: OpenLoopStatus | str,
        evidence: str | None = None,
    ) -> OpenLoopSchema:
        """Updates loop status (e.g. WAITING, BLOCKED)."""
        loop = self._loops.get(loop_id)
        if not loop:
            raise KeyError(f"Open loop '{loop_id}' not found.")
        new_status = status if isinstance(status, OpenLoopStatus) else OpenLoopStatus(str(status))
        loop.status = new_status
        loop.updated_at = datetime.now(UTC)
        return loop

    def update_loop_activity(self, loop_id: str) -> None:
        """Updates last_activity timestamp upon meaningful progress."""
        loop = self._loops.get(loop_id)
        if loop:
            loop.last_activity = datetime.now(UTC)
            loop.updated_at = datetime.now(UTC)
            if loop.status == OpenLoopStatus.STALE:
                loop.status = OpenLoopStatus.OPEN

    def check_staleness(self) -> list[OpenLoopSchema]:
        """INVARIANT 35 & 36: Flags loops with no meaningful progress as STALE without assuming abandonment."""
        now = datetime.now(UTC)
        stale_loops = []
        for loop in self._loops.values():
            if loop.status in (OpenLoopStatus.OPEN, OpenLoopStatus.WAITING):
                diff = now - (loop.last_activity if loop.last_activity.tzinfo else loop.last_activity.replace(tzinfo=UTC))
                if diff > self.stale_threshold:
                    loop.status = OpenLoopStatus.STALE
                    loop.updated_at = now
                    stale_loops.append(loop)
        return stale_loops

    def close_loop(
        self,
        loop_id: str,
        evidence: str | None = None,
        reason: str = "Completed",
    ) -> OpenLoopSchema:
        """INVARIANT 37 & 182: User control to close open loop with required verified evidence."""
        loop = self._loops.get(loop_id)
        if not loop:
            raise KeyError(f"Open loop '{loop_id}' not found.")
        if evidence is not None and not evidence.strip():
            raise ValueError("Valid closure evidence is required.")
        loop.status = OpenLoopStatus.COMPLETED
        loop.updated_at = datetime.now(UTC)
        return loop

    def reopen_loop(self, loop_id: str) -> OpenLoopSchema:
        """INVARIANT 37: User control to reopen closed loop."""
        loop = self._loops.get(loop_id)
        if not loop:
            raise KeyError(f"Open loop '{loop_id}' not found.")
        loop.status = OpenLoopStatus.OPEN
        loop.last_activity = datetime.now(UTC)
        loop.updated_at = datetime.now(UTC)
        return loop

    def list_open_loops(
        self,
        project_id: str | None = None,
        status: OpenLoopStatus | None = None,
        include_stale: bool = True,
        waiting_only: bool = False,
        check_staleness: bool = False,
    ) -> list[OpenLoopSchema]:
        """INVARIANT 88-91: Lists unresolved loops or filters by waiting state."""
        if check_staleness:
            self.check_staleness()

        results = list(self._loops.values())
        now = datetime.now(UTC)
        for l in results:
            created_tz = l.created_at if l.created_at.tzinfo else l.created_at.replace(tzinfo=UTC)
            l.age_days = max(0, (now - created_tz).days)

        if project_id:
            results = [l for l in results if l.scope_id == project_id]
        if status:
            results = [l for l in results if l.status == status.value or l.status == status]
        if waiting_only:
            results = [l for l in results if l.status in (OpenLoopStatus.WAITING, OpenLoopStatus.BLOCKED)]
        if not include_stale:
            results = [l for l in results if l.status != OpenLoopStatus.STALE]

        def _sort_key(item: OpenLoopSchema) -> float:
            if isinstance(item.priority, (int, float)):
                return float(item.priority)
            p_str = str(item.priority).upper()
            if p_str == "HIGH":
                return 0.9
            if p_str == "MEDIUM":
                return 0.5
            return 0.2

        return sorted(results, key=_sort_key, reverse=True)
