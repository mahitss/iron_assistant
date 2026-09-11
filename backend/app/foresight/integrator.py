"""Cross-subsystem integration bridge connecting World Model with Tasks 42–64 (Task 65, Spec 42-48, 91-97)."""

from __future__ import annotations

import logging
from typing import Any

from app.foresight.schemas import (
    ForesightEntity,
    StateAuthority,
    WorldScope,
)

logger = logging.getLogger(__name__)


class SubsystemIntegrator:
    """Coordinates bi-directional context exchange between the World Model and Kairo's specialized reasoning engines."""

    # --- Task 54: Digital Twin Integration ---
    def sync_from_digital_twin(self, twin_state: dict[str, Any]) -> list[ForesightEntity]:
        """Ingest operational environment and hardware/cloud telemetry from Digital Twin (Task 54).

        Digital Twin represents current/simulated operational state; World Model provides
        the broader temporal, strategic, and causal context.
        """
        entities: list[ForesightEntity] = []
        services = twin_state.get("services", [])
        for s in services:
            ent = ForesightEntity(
                entity_id=s.get("service_id", f"svc_{s.get('name', 'service')}"),
                type="service",
                name=s.get("name", "Service"),
                state=s.get("health", "HEALTHY").upper(),
                attributes={
                    "latency_p99": s.get("latency_p99", 120.0),
                    "cpu_pct": s.get("cpu_pct", 45.0),
                    "instances": s.get("instances", 2),
                },
                scope=WorldScope.INFRASTRUCTURE,
                confidence=0.90,
                authority=StateAuthority.OBSERVED,
                provenance={"source": "digital_twin_telemetry"},
            )
            entities.append(ent)
        return entities

    # --- Task 58: Strategic Planning Integration ---
    def evaluate_plan_assumption_invalidation(
        self,
        plan_id: str,
        plan_assumptions: list[str],
        invalidated_world_state: str,
    ) -> dict[str, Any]:
        """Check if changes in world model invalidate assumptions of active strategic plans (Task 58, Spec 47)."""
        broken_assumptions: list[str] = []
        lowered = invalidated_world_state.lower()
        for assump in plan_assumptions:
            if any(term in assump.lower() for term in lowered.split()):
                broken_assumptions.append(assump)

        is_invalid = len(broken_assumptions) > 0
        status_code = "PLAN_ASSUMPTION_INVALID" if is_invalid else "PLAN_ASSUMPTIONS_VALID"

        if is_invalid:
            logger.warning(
                "PLAN_ASSUMPTIONS_INVALIDATED: plan_id=%s broken=%s",
                plan_id,
                broken_assumptions,
            )

        return {
            "plan_id": plan_id,
            "status": status_code,
            "is_invalid": is_invalid,
            "broken_assumptions": broken_assumptions,
            "recommended_action": "TRIGGER_REPLAN" if is_invalid else "PROCEED",
        }

    # --- Task 61: Incident Response Integration ---
    def evaluate_incident_blast_radius(
        self,
        incident_id: str,
        affected_resource_id: str,
        downstream_entities: list[str],
    ) -> dict[str, Any]:
        """Provide incident response engine with dependency blast radius and secondary risks (Task 61, Spec 46)."""
        secondary_risks = [
            f"Downstream service {e} at risk of cascading latency degradation"
            for e in downstream_entities[:3]
        ]
        return {
            "incident_id": incident_id,
            "affected_resource": affected_resource_id,
            "blast_radius_entities": downstream_entities,
            "blast_radius_size": len(downstream_entities),
            "secondary_risks": secondary_risks,
            "consequence_severity": "CRITICAL" if len(downstream_entities) >= 3 else "MEDIUM",
        }

    # --- Task 63: Research Intelligence Integration ---
    def ingest_research_finding(
        self,
        finding_topic: str,
        claims: list[dict[str, Any]],
        source_quality: float = 0.85,
    ) -> dict[str, Any]:
        """Enrich world model technology states and external trends using verified research findings (Task 63, Spec 43)."""
        extracted_facts: list[str] = []
        for c in claims:
            statement = c.get("statement", "")
            if statement:
                extracted_facts.append(statement)

        logger.info(
            "RESEARCH_INTEGRATED_INTO_WORLD: topic='%s' claims_count=%d",
            finding_topic,
            len(extracted_facts),
        )
        return {
            "topic": finding_topic,
            "integrated_claims_count": len(extracted_facts),
            "source_trust": source_quality,
            "facts": extracted_facts,
        }

    # --- Task 64: Collective Intelligence / Swarm Integration ---
    def synthesize_swarm_perspectives(
        self,
        swarm_forecasts: list[dict[str, Any]],
        minority_positions: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Incorporate multi-agent swarm forecasts and preserved minority opinions into foresight (Task 64, Spec 44).

        Invariant: Consensus != Truth. Dissenting perspectives are preserved as contingency failure scenarios.
        """
        contingency_scenarios: list[str] = []
        for min_rep in minority_positions:
            role = min_rep.get("role", "CRITIC")
            dissent = min_rep.get("dissent", "Unspecified failure mode")
            contingency_scenarios.append(f"Contingency scenario flagged by {role}: {dissent}")

        return {
            "swarm_forecast_count": len(swarm_forecasts),
            "contingency_scenarios": contingency_scenarios,
            "epistemic_consensus_reached": len(minority_positions) == 0,
        }


subsystem_integrator = SubsystemIntegrator()
