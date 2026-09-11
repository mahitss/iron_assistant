"""Transactional facade service for Autonomous World Model & Long-Horizon Foresight Engine (Task 65)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from app.foresight.audit import AuditRecord, foresight_auditor
from app.foresight.causal_propagation import causal_propagation_engine
from app.foresight.consistency import world_model_consistency_checker
from app.foresight.early_warning import early_warning_engine
from app.foresight.entities import foresight_entity_manager
from app.foresight.forecasting import long_horizon_forecaster
from app.foresight.integrator import subsystem_integrator
from app.foresight.privacy import validate_tenant_access
from app.foresight.relationships import foresight_relationship_manager
from app.foresight.safety import (
    block_direct_foresight_action,
    sanitize_foresight_directive,
    validate_state_claim_evidence,
)
from app.foresight.scenarios import scenario_engine
from app.foresight.schemas import (
    EarlyWarningSeverity,
    EarlyWarningSignal,
    ForecastCreateRequest,
    ForecastRecord,
    ForesightEntity,
    ForesightHorizon,
    ForesightRelationship,
    RelationshipType,
    ScenarioBranch,
    ScenarioCreateRequest,
    ScenarioType,
    StateAuthority,
    StrategicOpportunity,
    StrategicRisk,
    UncertaintyGrade,
    WorldDiff,
    WorldModelOverview,
    WorldModelQueryRequest,
    WorldModelQueryResponse,
    WorldScope,
)
from app.foresight.strategic import strategic_foresight_manager
from app.foresight.temporal import temporal_world_manager

logger = logging.getLogger(__name__)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class ForesightService:
    """Central service coordinator for the Autonomous World Model & Long-Horizon Foresight Engine."""

    def __init__(self) -> None:
        self.entities = foresight_entity_manager
        self.relationships = foresight_relationship_manager
        self.temporal = temporal_world_manager
        self.causal = causal_propagation_engine
        self.forecasting = long_horizon_forecaster
        self.scenarios = scenario_engine
        self.early_warnings = early_warning_engine
        self.strategic = strategic_foresight_manager
        self.consistency = world_model_consistency_checker
        self.integrator = subsystem_integrator
        self.auditor = foresight_auditor
        self._world_id: str = "world_primary_01"
        self._scope: WorldScope = WorldScope.SYSTEM
        self._version: int = 1
        self._initialize_bootstrap_seed()

    def _initialize_bootstrap_seed(self) -> None:
        """Seed initial foundational entities and causal relationships."""
        # Services & Resources
        s1 = self.entities.upsert_entity(
            entity_id="svc_gateway",
            name="API Gateway",
            entity_type="service",
            state="HEALTHY",
            attributes={"qps": 12000, "latency_p99": 35.0},
            scope=WorldScope.INFRASTRUCTURE,
        )
        s2 = self.entities.upsert_entity(
            entity_id="svc_auth",
            name="Authentication Service",
            entity_type="service",
            state="HEALTHY",
            attributes={"auth_success_pct": 99.98},
            scope=WorldScope.INFRASTRUCTURE,
        )
        s3 = self.entities.upsert_entity(
            entity_id="svc_payment",
            name="Payment Processing Engine",
            entity_type="service",
            state="HEALTHY",
            attributes={"throughput_tps": 450},
            scope=WorldScope.INFRASTRUCTURE,
        )
        db1 = self.entities.upsert_entity(
            entity_id="db_primary",
            name="Primary Aurora PostgreSQL Database",
            entity_type="database",
            state="HEALTHY",
            attributes={"connections": 180, "cpu_pct": 52.0},
            scope=WorldScope.INFRASTRUCTURE,
        )
        res1 = self.entities.upsert_entity(
            entity_id="res_cluster_compute",
            name="Kubernetes Compute Cluster",
            entity_type="resource",
            state="AVAILABLE",
            attributes={"cpu_utilization_pct": 68.0, "memory_utilization_pct": 74.0},
            scope=WorldScope.INFRASTRUCTURE,
        )

        # Record initial version transitions
        for e in [s1, s2, s3, db1, res1]:
            self.temporal.record_state_transition(
                entity_id=e.entity_id,
                state=e.state,
                observed_at=e.valid_from,
                source="bootstrap",
            )

        # Causal & Dependency Edges
        self.relationships.add_relationship(
            source_entity_id="svc_gateway",
            target_entity_id="svc_auth",
            relationship_type=RelationshipType.DEPENDS_ON,
            is_critical=True,
        )
        self.relationships.add_relationship(
            source_entity_id="svc_gateway",
            target_entity_id="svc_payment",
            relationship_type=RelationshipType.DEPENDS_ON,
            is_critical=True,
        )
        self.relationships.add_relationship(
            source_entity_id="svc_payment",
            target_entity_id="db_primary",
            relationship_type=RelationshipType.DEPENDS_ON,
            is_critical=True,
        )
        self.relationships.add_relationship(
            source_entity_id="db_primary",
            target_entity_id="svc_payment",
            relationship_type=RelationshipType.CAUSES,
            causal_strength=0.92,
            evidence=["Stress tests prove database latency spikes cause payment queue stall"],
            is_critical=True,
        )

        # Strategic Risk & Opportunity
        self.strategic.register_risk(
            title="Database Connection Pool Saturation under Black Friday Peak",
            description="Peak concurrent transaction demand may exceed max Aurora connection limit (500).",
            probability=0.45,
            impact=0.85,
            time_horizon=ForesightHorizon.MID_FUTURE_1M,
            dependencies=["db_primary", "svc_payment"],
            evidence=["Historical seasonal peak telemetry from Q4 2025"],
        )
        self.strategic.register_opportunity(
            title="Asynchronous Transaction Buffering via Redis Edge Cache",
            description="Buffering write acknowledgments preserves 40% connection headroom during burst peaks.",
            potential_value=0.80,
            optionality_score=0.85,
            time_horizon=ForesightHorizon.MID_FUTURE_1M,
            dependencies=["db_primary"],
        )

        self.auditor.record_event(
            event_type="WORLD_MODEL_INITIALIZED",
            details={"entities": 5, "relationships": 4},
            actor="system",
        )

    # --- Query & Overview ---

    def get_overview(self, tenant_id: str = "default") -> WorldModelOverview:
        """Retrieve comprehensive high-level status of the world model."""
        ents = self.entities.list_entities(tenant_id=tenant_id)
        rels = self.relationships.list_relationships()
        fcts = self.forecasting.list_forecasts(tenant_id=tenant_id)
        scns = self.scenarios.list_scenarios(tenant_id=tenant_id)
        risks = self.strategic.list_risks()
        opps = self.strategic.list_opportunities()
        warns = self.early_warnings.list_warnings(active_only=True)

        inconsistencies = self.consistency.audit_consistency(
            entities={e.entity_id: e for e in ents},
            relationships=rels,
        )
        integrity = "HEALTHY" if not inconsistencies else f"DEGRADED ({len(inconsistencies)} issues)"

        return WorldModelOverview(
            world_id=self._world_id,
            scope=self._scope,
            version=self._version,
            entity_count=len(ents),
            relationship_count=len(rels),
            active_forecasts_count=len(fcts),
            active_scenarios_count=len(scns),
            open_risks_count=len(risks),
            open_opportunities_count=len(opps),
            early_warnings_count=len(warns),
            last_updated=_now_utc(),
            integrity_status=integrity,
        )

    def query_world_model(
        self,
        req: WorldModelQueryRequest,
        tenant_id: str = "default",
    ) -> WorldModelQueryResponse:
        """Reason across entities, relationships, forecasts, and risks to answer strategic questions (Spec 74)."""
        block_direct_foresight_action("query_world_model")
        cleaned_query = sanitize_foresight_directive(req.query)

        all_ents = self.entities.list_entities(tenant_id=tenant_id)
        ent_map = {e.entity_id: e for e in all_ents}

        # Filter relevant entities
        relevant: list[ForesightEntity] = []
        if req.target_entities:
            relevant = [ent_map[eid] for eid in req.target_entities if eid in ent_map]
        else:
            # Simple keyword matching
            q_lower = cleaned_query.lower()
            relevant = [e for e in all_ents if e.name.lower() in q_lower or e.type.lower() in q_lower][:5]

        # Extract causal paths / blast radius if relevant entities found
        causal_factors: list[str] = []
        if relevant and req.include_causal_path:
            rels = self.relationships.list_relationships()
            for r_ent in relevant[:2]:
                blast = self.causal.compute_blast_radius(r_ent.entity_id, rels)
                if blast:
                    causal_factors.append(
                        f"Entity '{r_ent.name}' propagates degradation to: {', '.join(blast)}"
                    )

        # Fetch scenarios and warnings
        scenarios: list[ScenarioBranch] = (
            self.scenarios.list_scenarios(tenant_id=tenant_id) if req.include_scenarios else []
        )
        warnings = self.early_warnings.list_warnings(active_only=True)

        uncertainty = UncertaintyGrade.KNOWN if len(relevant) >= 2 else UncertaintyGrade.LIKELY
        conf = 0.85 if uncertainty == UncertaintyGrade.KNOWN else 0.70

        answer = (
            f"Autonomous World Model analysis for query '{cleaned_query}': "
            f"Identified {len(relevant)} relevant entities with {len(causal_factors)} causal dependency paths. "
            f"Active risk and scenario projections indicate stable baseline operations with monitored dependencies."
        )

        explanation = (
            f"Belief state grounded in {len(relevant)} observed entities and {len(self.relationships.list_relationships())} "
            "relationships. All state assertions adhere to the invariant WORLD MODEL != REALITY."
        )

        return WorldModelQueryResponse(
            answer=answer,
            confidence=conf,
            uncertainty=uncertainty,
            relevant_entities=relevant,
            causal_factors=causal_factors,
            scenarios=scenarios,
            early_warnings=warnings,
            explanation=explanation,
        )

    # --- Entities & State Versioning ---

    def upsert_entity(
        self,
        entity_id: str,
        name: str,
        entity_type: str,
        state: str = "UNKNOWN",
        attributes: dict[str, Any] | None = None,
        scope: WorldScope = WorldScope.SYSTEM,
        confidence: float = 0.8,
        authority: StateAuthority = StateAuthority.OBSERVED,
        provenance: dict[str, Any] | None = None,
        tenant_id: str = "default",
        claim_evidence: list[str] | None = None,
    ) -> ForesightEntity:
        """Register or update an entity state, with state-poisoning defense and temporal versioning."""
        # Enforce State Poisoning Defense (Spec 80, 81)
        validate_state_claim_evidence(
            name, claim_evidence, source=provenance.get("source", "system") if provenance else "system"
        )
        validate_state_claim_evidence(
            state, claim_evidence, source=provenance.get("source", "system") if provenance else "system"
        )

        ent = self.entities.upsert_entity(
            entity_id=entity_id,
            name=name,
            entity_type=entity_type,
            state=state,
            attributes=attributes,
            scope=scope,
            confidence=confidence,
            authority=authority,
            provenance=provenance,
            tenant_id=tenant_id,
        )

        self.temporal.record_state_transition(
            entity_id=ent.entity_id,
            state=ent.state,
            observed_at=ent.valid_from,
            source=provenance.get("source", "system") if provenance else "system",
            confidence=confidence,
            authority=authority,
        )

        self._version += 1
        self.auditor.record_event(
            event_type="ENTITY_UPSERTED",
            details={"entity_id": ent.entity_id, "state": ent.state, "version": ent.version},
            actor=provenance.get("actor", "system") if provenance else "system",
            tenant_id=tenant_id,
        )
        return ent

    def get_entity(self, entity_id: str, tenant_id: str = "default") -> ForesightEntity | None:
        """Retrieve entity by ID with tenant validation."""
        ent = self.entities.get_entity(entity_id)
        if ent:
            validate_tenant_access(tenant_id, ent.tenant_id)
        return ent

    def list_entities(
        self,
        entity_type: str | None = None,
        scope: WorldScope | None = None,
        state: str | None = None,
        tenant_id: str = "default",
    ) -> list[ForesightEntity]:
        """List entities with optional filters."""
        return self.entities.list_entities(
            entity_type=entity_type,
            scope=scope,
            state=state,
            tenant_id=tenant_id,
        )

    # --- Relationships ---

    def add_relationship(
        self,
        source_entity_id: str,
        target_entity_id: str,
        relationship_type: RelationshipType = RelationshipType.DEPENDS_ON,
        causal_strength: float = 0.5,
        evidence: list[str] | None = None,
        confidence: float = 0.8,
        conditions: list[str] | None = None,
        scope: WorldScope = WorldScope.SYSTEM,
        is_critical: bool = False,
    ) -> ForesightRelationship:
        """Add semantic or causal relationship."""
        rel = self.relationships.add_relationship(
            source_entity_id=source_entity_id,
            target_entity_id=target_entity_id,
            relationship_type=relationship_type,
            causal_strength=causal_strength,
            evidence=evidence,
            confidence=confidence,
            conditions=conditions,
            scope=scope,
            is_critical=is_critical,
        )
        self.auditor.record_event(
            event_type="RELATIONSHIP_ADDED",
            details={"rel_id": rel.rel_id, "type": rel.relationship_type.value},
        )
        return rel

    def list_relationships(
        self,
        source_id: str | None = None,
        target_id: str | None = None,
        relationship_type: RelationshipType | None = None,
    ) -> list[ForesightRelationship]:
        """List relationships."""
        return self.relationships.list_relationships(
            source_id=source_id,
            target_id=target_id,
            relationship_type=relationship_type,
        )

    # --- Forecasting (Spec 75) ---

    def create_forecast(self, req: ForecastCreateRequest) -> ForecastRecord:
        """Create or generate a new range-based forecast."""
        fct = self.forecasting.generate_forecast(
            topic=req.topic,
            horizon=req.horizon,
            metric_name=req.target_metric,
            assumptions=req.assumptions,
            tenant_id=req.tenant_id,
        )
        self.auditor.record_event(
            event_type="FORECAST_GENERATED",
            details={"forecast_id": fct.forecast_id, "topic": fct.topic, "horizon": fct.horizon.value},
            tenant_id=req.tenant_id,
        )
        return fct

    def get_forecast(self, forecast_id: str) -> ForecastRecord | None:
        """Retrieve forecast by ID."""
        return self.forecasting.get_forecast(forecast_id)

    def list_forecasts(
        self,
        horizon: ForesightHorizon | None = None,
        tenant_id: str = "default",
    ) -> list[ForecastRecord]:
        """List forecasts."""
        return self.forecasting.list_forecasts(horizon=horizon, tenant_id=tenant_id)

    def record_forecast_outcome(self, forecast_id: str, actual_value: float) -> float:
        """Record real-world outcome and update forecast calibration score."""
        score = self.forecasting.record_actual_outcome(forecast_id, actual_value)
        self.auditor.record_event(
            event_type="FORECAST_CALIBRATED",
            details={"forecast_id": forecast_id, "actual": actual_value, "score": score},
        )
        return score

    # --- Scenarios (Spec 23-27) ---

    def create_scenario(self, req: ScenarioCreateRequest) -> ScenarioBranch:
        """Generate an isolated scenario branch sandbox."""
        all_ents = {e.entity_id: e for e in self.entities.list_entities(tenant_id=req.tenant_id)}
        branch = self.scenarios.create_scenario_branch(
            name=req.name,
            scenario_type=req.type,
            horizon=req.horizon,
            current_entities=all_ents,
            assumptions=req.assumptions,
            interventions=req.interventions,
            tenant_id=req.tenant_id,
        )
        self.auditor.record_event(
            event_type="SCENARIO_BRANCHED",
            details={
                "scenario_id": branch.scenario_id,
                "type": branch.type.value,
                "horizon": branch.horizon.value,
            },
            tenant_id=req.tenant_id,
        )
        return branch

    def get_scenario(self, scenario_id: str) -> ScenarioBranch | None:
        """Retrieve scenario branch by ID."""
        return self.scenarios.get_scenario(scenario_id)

    def list_scenarios(
        self,
        scenario_type: ScenarioType | None = None,
        tenant_id: str = "default",
    ) -> list[ScenarioBranch]:
        """List active scenario branches."""
        return self.scenarios.list_scenarios(scenario_type=scenario_type, tenant_id=tenant_id)

    # --- Risks, Opportunities & Early Warnings ---

    def list_risks(self, status: str = "OPEN") -> list[StrategicRisk]:
        """List strategic risks."""
        return self.strategic.list_risks(status=status)

    def list_opportunities(self, status: str = "IDENTIFIED") -> list[StrategicOpportunity]:
        """List strategic opportunities."""
        return self.strategic.list_opportunities(status=status)

    def list_early_warnings(self, active_only: bool = True) -> list[EarlyWarningSignal]:
        """List early warning signals."""
        return self.early_warnings.list_warnings(active_only=active_only)

    def emit_early_warning(
        self,
        title: str,
        description: str,
        severity: EarlyWarningSeverity = EarlyWarningSeverity.MEDIUM,
        affected_entities: list[str] | None = None,
    ) -> EarlyWarningSignal:
        """Emit an early warning signal."""
        signal = self.early_warnings.emit_early_warning(
            title=title,
            description=description,
            severity=severity,
            affected_entities=affected_entities,
        )
        self.auditor.record_event(
            event_type="EARLY_WARNING_EMITTED",
            details={"signal_id": signal.signal_id, "title": title, "severity": severity.value},
        )
        return signal

    # --- World Diff & Reassessment ---

    def compute_diff(self, historical_time: datetime) -> WorldDiff:
        """Compute structural difference between world at historical_time and current world (Spec 15)."""
        current_ents = {e.entity_id: e for e in self.entities.list_entities()}
        current_rels = {r.rel_id: r for r in self.relationships.list_relationships()}

        # Reconstruct historical entities
        historical_ents: dict[str, ForesightEntity] = {}
        for eid, ent in current_ents.items():
            hist_state = self.temporal.get_state_at_time(eid, historical_time)
            if hist_state:
                h_ent = ent.model_copy(update={"state": hist_state})
                historical_ents[eid] = h_ent

        return self.temporal.compute_diff(
            entities_a=historical_ents,
            entities_b=current_ents,
            relationships_a=current_rels,
            relationships_b=current_rels,
        )

    def reassess_world_model(
        self,
        changed_entity_id: str | None = None,
        reason: str = "routine_reassessment",
        invalidate_stale_forecasts: bool = True,
    ) -> dict[str, Any]:
        """Re-evaluate assumptions, detect newly broken conditions, and propagate staleness (Spec 27, 74)."""
        invalidated_forecasts: list[str] = []
        invalidated_scenarios: list[str] = []

        if changed_entity_id:
            ent = self.entities.get_entity(changed_entity_id)
            if ent and ent.state in ("FAILED", "DEGRADED"):
                # Invalidate dependent assumptions
                assump_key = f"{ent.name} remains healthy"
                invalidated_forecasts = self.forecasting.invalidate_on_assumption_failure(assump_key)
                invalidated_scenarios = self.scenarios.invalidate_on_assumption_change(assump_key)

        self._version += 1
        self.auditor.record_event(
            event_type="WORLD_MODEL_REASSESSED",
            details={
                "reason": reason,
                "changed_entity": changed_entity_id,
                "invalidated_forecasts": invalidated_forecasts,
                "invalidated_scenarios": invalidated_scenarios,
            },
        )

        return {
            "status": "reassessment_complete",
            "world_version": self._version,
            "invalidated_forecast_count": len(invalidated_forecasts),
            "invalidated_scenario_count": len(invalidated_scenarios),
            "invalidated_forecast_ids": invalidated_forecasts,
            "invalidated_scenario_ids": invalidated_scenarios,
        }

    def get_audit_trail(self, limit: int = 100) -> list[AuditRecord]:
        """Retrieve cryptographic audit records."""
        return self.auditor.get_audit_trail(limit=limit)

    def verify_audit_integrity(self) -> bool:
        """Verify unbroken SHA-256 chain integrity."""
        return self.auditor.verify_integrity()


foresight_service = ForesightService()
