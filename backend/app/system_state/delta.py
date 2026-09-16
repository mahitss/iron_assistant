"""State-Delta computation engine (Task 93 Phase 7).

Computes granular operational differentials between two snapshots and
identifies cascade effects on active tasks, workflows, and goals.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING
import uuid

from app.system_state.models import (
    DeltaType,
    EpistemicStatus,
    StateCategory,
    StateDelta,
    StateType,
)

if TYPE_CHECKING:
    from app.system_state.graph import SystemStateGraph
    from app.system_state.models import SystemStateSnapshot

UNHEALTHY_STATES = {
    StateCategory.DEGRADED,
    StateCategory.FAILED,
    StateCategory.UNAVAILABLE,
    StateCategory.BLOCKED,
}

HEALTHY_STATES = {
    StateCategory.HEALTHY,
    StateCategory.ACTIVE,
}


class StateDeltaEngine:
    """Computes operational differentials and maps cascading impact on active objectives."""

    def __init__(self, graph: SystemStateGraph | None = None) -> None:
        self._graph = graph

    def compute_deltas(
        self,
        snapshot_a: SystemStateSnapshot,
        snapshot_b: SystemStateSnapshot,
    ) -> list[StateDelta]:
        """Compare snapshot A (before) and snapshot B (after) and generate deltas."""
        deltas: list[StateDelta] = []
        now = datetime.now(UTC)

        entities_a = snapshot_a.entities
        entities_b = snapshot_b.entities

        # 1. Added entities
        for eid, ent_b in entities_b.items():
            if eid not in entities_a:
                d_type = DeltaType.NEW_INCIDENT if ent_b.state_type == StateType.INCIDENT else DeltaType.ADDED
                deltas.append(
                    StateDelta(
                        delta_id=f"dt_{uuid.uuid4().hex[:12]}",
                        from_snapshot_id=snapshot_a.snapshot_id,
                        to_snapshot_id=snapshot_b.snapshot_id,
                        delta_type=d_type,
                        entity_id=eid,
                        entity_type=ent_b.state_type,
                        from_status=None,
                        to_status=ent_b.status,
                        epistemic_status=ent_b.epistemic_status,
                        affected_tasks=self._find_affected_tasks(eid),
                        affected_workflows=self._find_affected_workflows(eid),
                        affected_goals=self._find_affected_goals(eid),
                        affected_dependencies=self._find_affected_dependencies(eid),
                        detected_at=now,
                        metadata={"confidence": ent_b.confidence},
                    )
                )

        # 2. Removed entities
        for eid, ent_a in entities_a.items():
            if eid not in entities_b:
                d_type = DeltaType.RESOLVED_INCIDENT if ent_a.state_type == StateType.INCIDENT else DeltaType.REMOVED
                deltas.append(
                    StateDelta(
                        delta_id=f"dt_{uuid.uuid4().hex[:12]}",
                        from_snapshot_id=snapshot_a.snapshot_id,
                        to_snapshot_id=snapshot_b.snapshot_id,
                        delta_type=d_type,
                        entity_id=eid,
                        entity_type=ent_a.state_type,
                        from_status=ent_a.status,
                        to_status=None,
                        epistemic_status=ent_a.epistemic_status,
                        affected_tasks=self._find_affected_tasks(eid),
                        affected_workflows=self._find_affected_workflows(eid),
                        affected_goals=self._find_affected_goals(eid),
                        affected_dependencies=self._find_affected_dependencies(eid),
                        detected_at=now,
                        metadata={},
                    )
                )

        # 3. Changed / Degraded / Recovered entities
        common_ids = set(entities_a.keys()) & set(entities_b.keys())
        for eid in common_ids:
            ent_a = entities_a[eid]
            ent_b = entities_b[eid]

            status_changed = ent_a.status != ent_b.status
            health_changed = abs(ent_a.health_score - ent_b.health_score) > 0.05

            if status_changed or health_changed:
                if ent_a.status in HEALTHY_STATES and ent_b.status in UNHEALTHY_STATES:
                    d_type = DeltaType.DEGRADED
                elif ent_a.status in UNHEALTHY_STATES and ent_b.status in HEALTHY_STATES:
                    d_type = DeltaType.RECOVERED
                elif ent_b.state_type == StateType.RESOURCE:
                    d_type = DeltaType.RESOURCE_CHANGE
                elif ent_b.state_type == StateType.GOAL and ent_b.status in UNHEALTHY_STATES:
                    d_type = DeltaType.GOAL_IMPACT
                elif ent_b.state_type == StateType.INCIDENT and ent_b.status in (StateCategory.HEALTHY, StateCategory.STOPPING):
                    d_type = DeltaType.RESOLVED_INCIDENT
                else:
                    d_type = DeltaType.CHANGED

                deltas.append(
                    StateDelta(
                        delta_id=f"dt_{uuid.uuid4().hex[:12]}",
                        from_snapshot_id=snapshot_a.snapshot_id,
                        to_snapshot_id=snapshot_b.snapshot_id,
                        delta_type=d_type,
                        entity_id=eid,
                        entity_type=ent_b.state_type,
                        from_status=ent_a.status,
                        to_status=ent_b.status,
                        epistemic_status=ent_b.epistemic_status,
                        affected_tasks=self._find_affected_tasks(eid),
                        affected_workflows=self._find_affected_workflows(eid),
                        affected_goals=self._find_affected_goals(eid),
                        affected_dependencies=self._find_affected_dependencies(eid),
                        detected_at=now,
                        metadata={
                            "old_health": ent_a.health_score,
                            "new_health": ent_b.health_score,
                        },
                    )
                )

        # 4. Topology Edge Changes (NEW_DEPENDENCY / LOST_DEPENDENCY)
        edges_a_keys = {(e.source_id, e.target_id, e.edge_type) for e in snapshot_a.edges}
        edges_b_keys = {(e.source_id, e.target_id, e.edge_type) for e in snapshot_b.edges}

        for s, t, et in edges_b_keys - edges_a_keys:
            deltas.append(
                StateDelta(
                    delta_id=f"dt_{uuid.uuid4().hex[:12]}",
                    from_snapshot_id=snapshot_a.snapshot_id,
                    to_snapshot_id=snapshot_b.snapshot_id,
                    delta_type=DeltaType.NEW_DEPENDENCY,
                    entity_id=s,
                    entity_type=StateType.DEPENDENCY,
                    from_status=None,
                    to_status=StateCategory.ACTIVE,
                    epistemic_status=EpistemicStatus.OBSERVED,
                    affected_tasks=self._find_affected_tasks(s),
                    affected_workflows=self._find_affected_workflows(s),
                    affected_goals=self._find_affected_goals(s),
                    affected_dependencies=[t],
                    detected_at=now,
                    metadata={"target_id": t, "edge_type": et.value},
                )
            )

        for s, t, et in edges_a_keys - edges_b_keys:
            deltas.append(
                StateDelta(
                    delta_id=f"dt_{uuid.uuid4().hex[:12]}",
                    from_snapshot_id=snapshot_a.snapshot_id,
                    to_snapshot_id=snapshot_b.snapshot_id,
                    delta_type=DeltaType.LOST_DEPENDENCY,
                    entity_id=s,
                    entity_type=StateType.DEPENDENCY,
                    from_status=StateCategory.ACTIVE,
                    to_status=None,
                    epistemic_status=EpistemicStatus.OBSERVED,
                    affected_tasks=self._find_affected_tasks(s),
                    affected_workflows=self._find_affected_workflows(s),
                    affected_goals=self._find_affected_goals(s),
                    affected_dependencies=[t],
                    detected_at=now,
                    metadata={"target_id": t, "edge_type": et.value},
                )
            )

        return deltas

    def _find_affected_tasks(self, entity_id: str) -> list[str]:
        if not self._graph:
            return []
        tasks = self._graph.tasks_affected_by(entity_id)
        return [t.id for t in tasks]

    def _find_affected_workflows(self, entity_id: str) -> list[str]:
        if not self._graph:
            return []
        impacted = self._graph.impact_of(entity_id)
        return [w.id for w in impacted if w.state_type == StateType.WORKFLOW]

    def _find_affected_goals(self, entity_id: str) -> list[str]:
        if not self._graph:
            return []
        goals = self._graph.goals_affected_by(entity_id)
        return [g.id for g in goals]

    def _find_affected_dependencies(self, entity_id: str) -> list[str]:
        if not self._graph:
            return []
        deps = self._graph.dependencies_of(entity_id)
        return [d.id for d in deps]
