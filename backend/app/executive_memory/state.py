"""Executive state synthesis aggregating from authoritative subsystems (INVARIANTS 2-6, 123)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
import uuid

from app.executive_memory.blockers import BlockerManager
from app.executive_memory.next_actions import NextActionEngine
from app.executive_memory.open_loops import OpenLoopManager
from app.executive_memory.provenance import ExecutiveProvenanceTracker
from app.executive_memory.safety import ExecutiveSafetyGuard
from app.executive_memory.schemas import ExecutiveStateScope, ExecutiveStateSchema


class ExecutiveStateManager:
    """Derives current executive state strictly from authoritative subsystems without competing with canonical truth."""

    def __init__(
        self,
        open_loop_mgr: OpenLoopManager,
        blocker_mgr: BlockerManager,
        next_action_engine: NextActionEngine,
    ) -> None:
        self.open_loop_mgr = open_loop_mgr
        self.blocker_mgr = blocker_mgr
        self.next_action_engine = next_action_engine
        # state_id -> ExecutiveStateSchema
        self._states: dict[str, ExecutiveStateSchema] = {}

    def synthesize_current_state(
        self,
        scope: ExecutiveStateScope = ExecutiveStateScope.PROJECT,
        scope_id: str | None = None,
        authoritative_sources: dict[str, Any] | None = None,
    ) -> ExecutiveStateSchema:
        """INVARIANT 4 & 5: Current state derived from authoritative systems (Projects, Tasks, Goals, World Model)."""
        sources = authoritative_sources or {}
        now = datetime.now(UTC)
        sid = f"exs_{uuid.uuid4().hex[:12]}"

        active_projects = sources.get("projects", [])
        active_goals = sources.get("goals", [])
        active_tasks = sources.get("tasks", [])
        recent_decisions = sources.get("decisions", [])
        recent_outcomes = sources.get("outcomes", [])
        upcoming_deadlines = sources.get("deadlines", [])
        pending_commitments = sources.get("commitments", [])
        risks = sources.get("risks", [])

        # Gather active blockers and open loops
        blockers = self.blocker_mgr.list_blockers(active_only=True)
        open_loops = self.open_loop_mgr.list_open_loops(project_id=scope_id)
        next_actions = self.next_action_engine.list_next_actions(project_id=scope_id)

        provenance = ExecutiveProvenanceTracker.create_provenance(
            source_system="AUTHORITATIVE_SYNTHESIS",
            source_id=scope_id or "global",
            metadata={"source_keys": list(sources.keys())},
        )

        state = ExecutiveStateSchema(
            state_id=sid,
            scope=scope,
            scope_id=scope_id,
            timestamp=now,
            active_projects=active_projects,
            active_goals=active_goals,
            active_tasks=active_tasks,
            blockers=blockers,
            open_loops=open_loops,
            recent_decisions=recent_decisions,
            recent_outcomes=recent_outcomes,
            upcoming_deadlines=upcoming_deadlines,
            pending_commitments=pending_commitments,
            next_actions=next_actions,
            risks=risks,
            confidence=1.0 if sources else 0.8,
            provenance=provenance,
            created_at=now,
        )
        self._states[sid] = state
        return state

    def get_state(self, state_id: str) -> ExecutiveStateSchema | None:
        return self._states.get(state_id)
