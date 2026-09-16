"""Structured Self-Model Query Engine (Task 93 Phase 18).

Provides authoritative, structured answers to Kairo's introspective self-model questions
linking active tasks, goals, capabilities, resource constraints, and epistemological boundaries.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from app.system_state.models import (
    EpistemicStatus,
    SelfModelAnswers,
    StateCategory,
    StateType,
)

if TYPE_CHECKING:
    from app.system_state.graph import SystemStateGraph
    from app.system_state.models import StateDelta


class SelfModelQueryEngine:
    """Answers Kairo's canonical self-model questions through the state graph."""

    def __init__(self, graph: SystemStateGraph) -> None:
        self._graph = graph

    def answer_all(self, recent_deltas: list[StateDelta] | None = None) -> SelfModelAnswers:
        """Synthesize answers to all 13 canonical operational questions."""
        now = datetime.now(UTC)
        entities = self._graph.list_entities()

        # 1. What am I doing?
        active_work = [
            {
                "entity_id": e.id,
                "type": e.state_type.value,
                "status": e.status.value,
                "health": e.health_score,
                "metadata": e.metadata,
            }
            for e in entities
            if e.state_type in (StateType.TASK, StateType.WORKFLOW)
            and e.status in (StateCategory.ACTIVE, StateCategory.STARTING)
        ]

        # 2. Why am I doing it? (Map active tasks/workflows upstream to goals)
        why_am_i_doing_it = []
        for work_item in active_work:
            eid = work_item["entity_id"]
            goals = self._graph.goals_affected_by(eid)
            why_am_i_doing_it.append(
                {
                    "work_id": eid,
                    "type": work_item["type"],
                    "serving_goals": [{"goal_id": g.id, "status": g.status.value, "meta": g.metadata} for g in goals],
                }
            )

        # 3. What am I waiting for?
        waiting_for = [
            {
                "entity_id": e.id,
                "type": e.state_type.value,
                "status": e.status.value,
                "blockers": [b.id for b in self._graph.blockers_for(e.id)] if e.state_type == StateType.GOAL else [],
                "meta": e.metadata,
            }
            for e in entities
            if e.status in (StateCategory.BLOCKED, StateCategory.SUSPENDED, StateCategory.STARTING)
        ]

        # 4. What is currently broken?
        broken = [
            {
                "entity_id": e.id,
                "type": e.state_type.value,
                "status": e.status.value,
                "health": e.health_score,
                "epistemic": e.epistemic_status.value,
                "source": e.source,
            }
            for e in entities
            if e.status in (StateCategory.FAILED, StateCategory.UNAVAILABLE, StateCategory.DEGRADED)
        ]

        # 5. What depends on this component? (Summary map of key broken/active components)
        dependents_map: dict[str, list[str]] = {}
        for b in broken[:20]:
            dependents_map[b["entity_id"]] = [d.id for d in self._graph.dependents_of(b["entity_id"])]

        # 6. What goals are blocked?
        goals_blocked = [
            {
                "goal_id": e.id,
                "status": e.status.value,
                "blockers": [b.id for b in self._graph.blockers_for(e.id)],
                "meta": e.metadata,
            }
            for e in entities
            if e.state_type == StateType.GOAL and (e.status == StateCategory.BLOCKED or bool(self._graph.blockers_for(e.id)))
        ]

        # 7. What resources are constrained?
        resources_constrained: dict[str, Any] = {
            "constrained_pools": [
                {"id": e.id, "status": e.status.value, "health": e.health_score, "meta": e.metadata}
                for e in entities
                if e.state_type == StateType.RESOURCE and e.status in (StateCategory.DEGRADED, StateCategory.FAILED)
            ]
        }

        # 8. What changed recently?
        changes = [
            {
                "delta_id": d.delta_id,
                "type": d.delta_type.value,
                "entity_id": d.entity_id,
                "from_status": d.from_status.value if d.from_status else None,
                "to_status": d.to_status.value if d.to_status else None,
                "detected_at": d.detected_at.isoformat(),
            }
            for d in (recent_deltas or [])[:50]
        ]

        # 9. What capabilities are degraded?
        degraded_capabilities = [
            {
                "capability_id": e.id,
                "status": e.status.value,
                "health": e.health_score,
                "impacted_goals": [g.id for g in self._graph.goals_affected_by(e.id)],
            }
            for e in entities
            if e.state_type == StateType.CAPABILITY and e.status in (StateCategory.DEGRADED, StateCategory.FAILED, StateCategory.UNAVAILABLE)
        ]

        # 10. What incidents are active?
        active_incidents = [
            {
                "incident_id": e.id,
                "status": e.status.value,
                "health": e.health_score,
                "meta": e.metadata,
                "affected_components": [imp.id for imp in self._graph.impact_of(e.id)],
            }
            for e in entities
            if e.state_type == StateType.INCIDENT and e.status not in (StateCategory.HEALTHY, StateCategory.STOPPING)
        ]

        # 11. What do I not know about my own state? (Epistemic UNKNOWN)
        unknown_states = [
            {
                "entity_id": e.id,
                "type": e.state_type.value,
                "reason": "Missing heartbeat or unverified observation",
                "source": e.source,
            }
            for e in entities
            if e.epistemic_status == EpistemicStatus.UNKNOWN or e.status == StateCategory.UNKNOWN
        ]

        # 12. What state information is stale?
        stale_states = [
            {
                "entity_id": e.id,
                "type": e.state_type.value,
                "last_updated": e.updated_at.isoformat(),
                "ttl_seconds": e.ttl_seconds,
            }
            for e in entities
            if e.status == StateCategory.STALE or e.is_stale(now)
        ]

        # 13. Which assumptions are inferred rather than observed?
        inferred_assumptions = [
            {
                "entity_id": e.id,
                "type": e.state_type.value,
                "epistemic_status": e.epistemic_status.value,
                "confidence": e.confidence,
                "meta": e.metadata,
            }
            for e in entities
            if e.epistemic_status in (EpistemicStatus.INFERRED, EpistemicStatus.PREDICTED, EpistemicStatus.DERIVED)
        ]

        return SelfModelAnswers(
            what_am_i_doing=active_work,
            why_am_i_doing_it=why_am_i_doing_it,
            what_am_i_waiting_for=waiting_for,
            what_is_broken=broken,
            what_depends_on_component=dependents_map,
            what_goals_are_blocked=goals_blocked,
            what_resources_are_constrained=resources_constrained,
            what_changed_recently=changes,
            what_capabilities_are_degraded=degraded_capabilities,
            what_incidents_are_active=active_incidents,
            what_do_i_not_know=unknown_states,
            what_state_is_stale=stale_states,
            which_assumptions_are_inferred=inferred_assumptions,
            queried_at=now,
        )
