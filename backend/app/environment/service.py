"""Environment Service master orchestrator for Kairo Environmental Intelligence & Digital Twin (Task 54)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.environment.auto_healing import AutoHealingGovernor
from app.environment.changes import ChangeDetector
from app.environment.digital_twin import DigitalTwinEngine
from app.environment.drift import DriftDetector
from app.environment.edges import create_environment_edge
from app.environment.evaluation import EnvironmentEvaluationEngine
from app.environment.health import HealthManager
from app.environment.incidents import IncidentManager
from app.environment.nodes import create_environment_node
from app.environment.remediation import RemediationManager
from app.environment.retrieval import ContextRetrievalManager
from app.environment.schemas import (
    ChangeType,
    DigitalTwin,
    DriftType,
    EnvironmentChange,
    EnvironmentDrift,
    EnvironmentEdge,
    EnvironmentNode,
    EnvironmentSnapshot,
    HealthEvidence,
    HealthRecord,
    HealthStatus,
    ImpactLevel,
    Incident,
    IncidentStatus,
    NodeType,
    RelationshipConfidence,
    RelationshipType,
    RemediationPlan,
    ScopeType,
    WhatIfSimulationResult,
)
from app.environment.snapshots import SnapshotManager
from app.environment.temporal import utc_now
from app.environment.topology import TopologyGraph
from app.environment.what_if import WhatIfSimulator


class EnvironmentService:
    """Unified service for the digital twin engine, topology analysis, operational awareness, and governed remediation."""

    def __init__(self, db: AsyncSession | None = None) -> None:
        self.db = db
        # In-memory twin stores keyed by (scope, scope_id)
        self._twins: dict[str, DigitalTwin] = {}
        self._drifts: dict[str, EnvironmentDrift] = {}
        self._incidents: dict[str, Incident] = {}
        self._snapshots: list[EnvironmentSnapshot] = []
        self._remediation_plans: dict[str, RemediationPlan] = {}
        self._auto_healing_governor = AutoHealingGovernor()

    def _twin_key(self, scope: ScopeType, scope_id: str | None = None) -> str:
        return f"{scope.value}:{scope_id or 'default'}"

    def get_or_create_twin(self, scope: ScopeType = ScopeType.SYSTEM, scope_id: str | None = None) -> DigitalTwin:
        """Retrieves active digital twin for scope, or initializes one if not present."""
        key = self._twin_key(scope, scope_id)
        if key not in self._twins:
            self._twins[key] = DigitalTwinEngine.create_twin(scope=scope, scope_id=scope_id)
        return self._twins[key]

    def register_node(
        self,
        node_id: str,
        node_type: NodeType,
        canonical_id: str,
        display_name: str,
        metadata: dict[str, Any] | None = None,
        scope: ScopeType = ScopeType.SYSTEM,
        scope_id: str | None = None,
        status: str = "UNKNOWN",
        provenance: dict[str, Any] | None = None,
        confidence: float = 1.0,
    ) -> EnvironmentNode:
        """Registers and validates a node into the digital twin."""
        node = create_environment_node(
            node_id=node_id,
            node_type=node_type,
            canonical_id=canonical_id,
            display_name=display_name,
            metadata=metadata,
            scope=scope,
            scope_id=scope_id,
            status=status,
            provenance=provenance,
            confidence=confidence,
        )
        twin = self.get_or_create_twin(scope, scope_id)
        DigitalTwinEngine.upsert_node(twin, node)
        return node

    def register_edge(
        self,
        source: str,
        relationship: RelationshipType,
        target: str,
        confidence: RelationshipConfidence = RelationshipConfidence.OBSERVED,
        provenance: dict[str, Any] | None = None,
        scope: ScopeType = ScopeType.SYSTEM,
        scope_id: str | None = None,
        is_same_environment_only: bool = False,
    ) -> EnvironmentEdge:
        """Registers a directional dependency or topology relationship while preventing false topology."""
        edge = create_environment_edge(
            source=source,
            relationship=relationship,
            target=target,
            confidence=confidence,
            provenance=provenance,
            is_same_environment_only=is_same_environment_only,
        )
        twin = self.get_or_create_twin(scope, scope_id)
        DigitalTwinEngine.upsert_edge(twin, edge)
        return edge

    def record_node_health(
        self,
        node_id: str,
        evidences: list[HealthEvidence],
        scope: ScopeType = ScopeType.SYSTEM,
        scope_id: str | None = None,
    ) -> HealthRecord:
        """Evaluates health based on concrete evidence. If evidence is missing, status is UNKNOWN."""
        twin = self.get_or_create_twin(scope, scope_id)
        health_record = HealthManager.aggregate_node_health(node_id, evidences)
        DigitalTwinEngine.update_node_health(twin, node_id, health_record)
        return health_record

    def record_change(
        self,
        resource_id: str,
        change_type: ChangeType,
        before: dict[str, Any] | None,
        after: dict[str, Any] | None,
        source: str,
        scope: ScopeType = ScopeType.SYSTEM,
        scope_id: str | None = None,
        verification: dict[str, Any] | None = None,
    ) -> EnvironmentChange:
        """Records an observed change event in the twin."""
        change = ChangeDetector.create_change_record(
            resource_id=resource_id,
            change_type=change_type,
            before=before,
            after=after,
            source=source,
            verification=verification,
        )
        twin = self.get_or_create_twin(scope, scope_id)
        DigitalTwinEngine.record_change(twin, change)
        return change

    def record_drift(
        self,
        resource_id: str,
        drift_type: DriftType,
        expected: dict[str, Any],
        actual: dict[str, Any],
        evidence: dict[str, Any] | None = None,
    ) -> EnvironmentDrift:
        """Registers an observed divergence between expected and actual state."""
        drift = DriftDetector.create_drift_record(
            resource_id=resource_id,
            drift_type=drift_type,
            expected=expected,
            actual=actual,
            evidence=evidence,
        )
        self._drifts[drift.drift_id] = drift
        return drift

    def create_snapshot(self, scope: ScopeType = ScopeType.SYSTEM, scope_id: str | None = None) -> EnvironmentSnapshot:
        """Takes an immutable point-in-time snapshot of the digital twin."""
        twin = self.get_or_create_twin(scope, scope_id)
        snapshot = SnapshotManager.create_snapshot(twin)
        self._snapshots.append(snapshot)
        return snapshot

    def get_state_as_of(
        self,
        as_of_time: datetime | str,
        scope: ScopeType = ScopeType.SYSTEM,
        scope_id: str | None = None,
    ) -> EnvironmentSnapshot | None:
        """Reconstructs historical state as of a specified moment, strictly prohibiting future leakage."""
        scoped_snapshots = [
            s for s in self._snapshots
            if s.scope == scope and (s.scope_id == scope_id or scope_id is None)
        ]
        return SnapshotManager.reconstruct_as_of(scoped_snapshots, as_of_time)

    def create_incident(
        self,
        scope: ScopeType,
        symptoms: list[str],
        affected_resources: list[str],
        evidence: dict[str, Any],
        suspected_cause: str | None = None,
        root_cause: str | None = None,
        scope_id: str | None = None,
    ) -> Incident:
        """Creates a tracked environment incident."""
        incident = IncidentManager.create_incident(
            scope=scope,
            symptoms=symptoms,
            affected_resources=affected_resources,
            evidence=evidence,
            suspected_cause=suspected_cause,
            root_cause=root_cause,
            scope_id=scope_id,
        )
        self._incidents[incident.incident_id] = incident
        return incident

    def estimate_blast_radius(
        self,
        origin_node_id: str,
        scope: ScopeType = ScopeType.SYSTEM,
        scope_id: str | None = None,
    ) -> dict[str, Any]:
        """Calculates potential downstream blast radius for a given origin node."""
        twin = self.get_or_create_twin(scope, scope_id)
        topology = TopologyGraph(twin.nodes, twin.edges)
        return IncidentManager.estimate_blast_radius(origin_node_id, topology)

    def simulate_what_if(
        self,
        target_node_id: str,
        event: str = "service_outage",
        scope: ScopeType = ScopeType.SYSTEM,
        scope_id: str | None = None,
    ) -> WhatIfSimulationResult:
        """Executes a hypothetical what-if simulation on the topology."""
        twin = self.get_or_create_twin(scope, scope_id)
        topology = TopologyGraph(twin.nodes, twin.edges)
        return WhatIfSimulator.simulate_node_failure(target_node_id, topology, hypothetical_event=event)

    def propose_remediation_plan(
        self,
        target: str,
        current_state: dict[str, Any],
        desired_state: dict[str, Any],
        risk: ImpactLevel = ImpactLevel.MEDIUM,
        dependencies: list[str] | None = None,
        rollback_target: dict[str, Any] | None = None,
        rollback_verified: bool = False,
        is_production: bool = False,
    ) -> RemediationPlan:
        """Creates a verifiable remediation plan with rollback target."""
        plan = RemediationManager.create_change_plan(
            target=target,
            current_state=current_state,
            desired_state=desired_state,
            risk=risk,
            dependencies=dependencies or [],
            rollback_target=rollback_target,
            rollback_verified=rollback_verified,
            is_production=is_production,
        )
        self._remediation_plans[plan.plan_id] = plan
        return plan

    def execute_auto_healing(
        self,
        resource_id: str,
        plan_id: str,
        is_pre_authorized: bool = True,
    ) -> bool:
        """Executes auto-healing under the governor with bounded attempt budgets."""
        plan = self._remediation_plans.get(plan_id)
        if not plan:
            return False
        return self._auto_healing_governor.request_auto_healing(resource_id, plan, is_pre_authorized=is_pre_authorized)

    # Topology Query Handlers (Prompts #155-#162)
    def query_dependents(self, node_id: str, scope: ScopeType = ScopeType.SYSTEM) -> list[str]:
        """Prompt #155: 'What depends on service X?'"""
        twin = self.get_or_create_twin(scope)
        topology = TopologyGraph(twin.nodes, twin.edges)
        return topology.get_downstream_dependents(node_id)

    def query_dependencies(self, node_id: str, scope: ScopeType = ScopeType.SYSTEM) -> list[str]:
        """Prompt #156: 'What does service X depend on?'"""
        twin = self.get_or_create_twin(scope)
        topology = TopologyGraph(twin.nodes, twin.edges)
        return topology.get_upstream_dependencies(node_id)

    def query_unhealthy_resources(self, scope: ScopeType = ScopeType.SYSTEM) -> list[dict[str, Any]]:
        """Prompt #158: 'What's currently unhealthy?'"""
        twin = self.get_or_create_twin(scope)
        unhealthy = []
        for nid, rec in twin.health.items():
            if rec.status in (HealthStatus.UNHEALTHY, HealthStatus.DEGRADED):
                node = twin.nodes.get(nid)
                unhealthy.append({
                    "node_id": nid,
                    "display_name": node.display_name if node else nid,
                    "status": rec.status.value,
                    "reason": rec.reason,
                    "evidence": [e.model_dump() for e in rec.evidence],
                })
        return unhealthy

    def query_production_resources(self) -> list[dict[str, Any]]:
        """Prompt #160: 'What's running in production?'"""
        prod_nodes = []
        for twin in self._twins.values():
            for n in twin.nodes.values():
                meta = n.metadata
                if meta.get("environment") in ("PRODUCTION", "PROD") or n.scope == ScopeType.ENVIRONMENT:
                    prod_nodes.append(n.model_dump())
        return prod_nodes

    def get_environment_context(
        self,
        task_query: str,
        focus_node_ids: list[str] | None = None,
        scope: ScopeType = ScopeType.SYSTEM,
    ) -> dict[str, Any]:
        """Prompt #175-#180: Extracts ranked, selective context for LLM prompt injections."""
        twin = self.get_or_create_twin(scope)
        return ContextRetrievalManager.extract_relevant_context(
            twin=twin,
            task_query=task_query,
            focus_node_ids=focus_node_ids,
        )

    def generate_environment_summary(self, scope: ScopeType = ScopeType.SYSTEM) -> dict[str, Any]:
        """Prompt #163-#165: Generates comprehensive summary of state, health, drift, and incidents."""
        twin = self.get_or_create_twin(scope)
        metrics = EnvironmentEvaluationEngine.evaluate_twin_metrics(twin)
        open_incidents = [i.model_dump() for i in self._incidents.values() if i.status != IncidentStatus.RESOLVED]
        active_drifts = [d.model_dump() for d in self._drifts.values() if d.status == "DETECTED"]

        return {
            "scope": scope.value,
            "version": twin.version,
            "freshness": twin.freshness.value,
            "confidence": twin.confidence,
            "metrics": metrics,
            "active_drifts_count": len(active_drifts),
            "active_drifts": active_drifts,
            "open_incidents_count": len(open_incidents),
            "open_incidents": open_incidents,
            "recent_changes_count": len(twin.changes),
            "recent_changes": [c.model_dump() for c in twin.changes[-10:]],
            "generated_at": utc_now().isoformat(),
        }


environment_service = EnvironmentService()

