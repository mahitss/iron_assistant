"""Structured System Self-Diagnostics Engine (Task 93 Phase 17).

Computes comprehensive diagnostic assessments of Kairo's operational health,
active objectives, resource constraints, and unverified assumptions.

CRITICAL INVARIANT:
Persist structured diagnostics only. Never persist hidden reasoning traces or pseudo-thoughts.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from app.system_state.models import (
    EpistemicStatus,
    StateCategory,
    StateType,
    SystemDiagnosis,
)

if TYPE_CHECKING:
    from app.system_state.graph import SystemStateGraph


class SystemDiagnosticsEngine:
    """Evaluates the operational state graph and produces structured system self-diagnostics."""

    def __init__(self, graph: SystemStateGraph) -> None:
        self._graph = graph

    def generate_diagnosis(self) -> SystemDiagnosis:
        """Analyze the operational graph and synthesize a structured diagnosis."""
        entities = self._graph.list_entities()
        now = datetime.now(UTC)

        # 1. Epistemic breakdown
        epistemic_counts: dict[str, int] = {
            EpistemicStatus.OBSERVED.value: 0,
            EpistemicStatus.DERIVED.value: 0,
            EpistemicStatus.INFERRED.value: 0,
            EpistemicStatus.PREDICTED.value: 0,
            EpistemicStatus.UNKNOWN.value: 0,
        }
        for e in entities:
            epistemic_counts[e.epistemic_status.value] = epistemic_counts.get(e.epistemic_status.value, 0) + 1

        # 2. Active objectives & work
        active_objectives = [
            {"id": e.id, "status": e.status.value, "health": e.health_score, "meta": e.metadata}
            for e in entities
            if e.state_type == StateType.GOAL and e.status in (StateCategory.ACTIVE, StateCategory.HEALTHY)
        ]
        active_work = [
            {"id": e.id, "type": e.state_type.value, "status": e.status.value, "meta": e.metadata}
            for e in entities
            if e.state_type in (StateType.TASK, StateType.WORKFLOW)
            and e.status in (StateCategory.ACTIVE, StateCategory.STARTING)
        ]

        # 3. Resource pressure
        resource_entities = [e for e in entities if e.state_type == StateType.RESOURCE]
        degraded_resources = [e for e in resource_entities if e.status in (StateCategory.DEGRADED, StateCategory.FAILED)]
        resource_pressure: dict[str, Any] = {
            "total_pools": len(resource_entities),
            "constrained_pools": len(degraded_resources),
            "details": [{"id": r.id, "status": r.status.value, "health": r.health_score} for r in degraded_resources],
        }

        # 4. Dependency issues
        dependency_issues = [
            {"id": e.id, "status": e.status.value, "epistemic": e.epistemic_status.value}
            for e in entities
            if e.state_type in (StateType.DEPENDENCY, StateType.EXTERNAL_DEPENDENCY)
            and e.status in (StateCategory.DEGRADED, StateCategory.FAILED, StateCategory.UNAVAILABLE)
        ]

        # 5. Security & Governance
        security_restrictions = [
            {"id": e.id, "status": e.status.value, "meta": e.metadata}
            for e in entities
            if e.state_type == StateType.SECURITY and e.status != StateCategory.HEALTHY
        ]
        governance_blockers = [
            {"id": e.id, "status": e.status.value, "meta": e.metadata}
            for e in entities
            if e.state_type == StateType.GOVERNANCE and e.status == StateCategory.BLOCKED
        ]

        # 6. Active Incidents
        active_incidents = [
            {
                "id": e.id,
                "status": e.status.value,
                "health": e.health_score,
                "meta": e.metadata,
                "impacted_entities": [imp.id for imp in self._graph.impact_of(e.id)],
            }
            for e in entities
            if e.state_type == StateType.INCIDENT and e.status not in (StateCategory.HEALTHY, StateCategory.STOPPING)
        ]

        # 7. Stale Knowledge
        stale_knowledge = [
            {"id": e.id, "status": e.status.value, "updated_at": e.updated_at.isoformat()}
            for e in entities
            if e.state_type == StateType.KNOWLEDGE and (e.status == StateCategory.STALE or e.is_stale(now))
        ]

        # 8. Predicted Risks & Counterfactuals (EpistemicStatus.PREDICTED)
        predicted_risks = [
            {"id": e.id, "confidence": e.confidence, "meta": e.metadata}
            for e in entities
            if e.epistemic_status == EpistemicStatus.PREDICTED
        ]

        # 9. Recovery Actions
        recovery_actions = [
            {"id": e.id, "type": e.state_type.value, "status": e.status.value}
            for e in entities
            if e.status in (StateCategory.RECOVERING, StateCategory.CANARY)
        ]

        # 10. Unknown / Unverified State
        unknown_states = [
            {"id": e.id, "type": e.state_type.value, "source": e.source}
            for e in entities
            if e.epistemic_status == EpistemicStatus.UNKNOWN or e.status == StateCategory.UNKNOWN
        ]

        # Overall composite health calculation
        if entities:
            avg_health = sum(e.health_score for e in entities) / len(entities)
        else:
            avg_health = 1.0

        if security_restrictions or any(e["status"] == StateCategory.BLOCKED.value for e in active_objectives):
            current_state = StateCategory.BLOCKED
            avg_health = min(avg_health, 0.4)
        elif active_incidents or any(e.status == StateCategory.FAILED for e in entities):
            current_state = StateCategory.FAILED
            avg_health = min(avg_health, 0.5)
        elif degraded_resources or dependency_issues or any(e.status == StateCategory.DEGRADED for e in entities):
            current_state = StateCategory.DEGRADED
            avg_health = min(avg_health, 0.75)
        elif recovery_actions:
            current_state = StateCategory.RECOVERING
        else:
            current_state = StateCategory.HEALTHY

        return SystemDiagnosis(
            current_state=current_state,
            health_score=round(avg_health, 4),
            active_objectives=active_objectives,
            active_work=active_work,
            resource_pressure=resource_pressure,
            dependency_issues=dependency_issues,
            security_restrictions=security_restrictions,
            governance_blockers=governance_blockers,
            active_incidents=active_incidents,
            stale_knowledge=stale_knowledge,
            predicted_risks=predicted_risks,
            recovery_actions=recovery_actions,
            unknown_states=unknown_states,
            epistemic_breakdown=epistemic_counts,
            diagnosed_at=now,
        )
