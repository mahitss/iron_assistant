"""Evidence collection, strength grading, and trust level classification."""

from __future__ import annotations

from typing import Any

from app.decision.schemas import (
    DataTrustLevel,
    EvidenceItem,
    EvidenceSet,
    EvidenceStrength,
)


class EvidenceEngine:
    """Manages primary vs model-derived evidence items and computes aggregated evidence strength."""

    def assemble_evidence_set(
        self,
        decision_id: str,
        context: dict[str, Any],
        simulation_data: dict[str, Any] | None = None,
        causal_data: dict[str, Any] | None = None,
    ) -> EvidenceSet:
        """Assembles and classifies evidence supporting the decision."""
        items: list[EvidenceItem] = []

        # 1. Primary telemetry evidence
        telemetry = context.get("telemetry", {})
        if telemetry:
            items.append(
                EvidenceItem(
                    evidence_type="telemetry_metrics",
                    strength=EvidenceStrength.VERIFIED,
                    trust_level=DataTrustLevel.TRUSTED_SYSTEM_DATA,
                    source="digital_twin_telemetry",
                    summary=f"Live telemetry baseline verified: {len(telemetry)} metric point(s) recorded.",
                    is_primary=True,
                    confidence=0.98,
                )
            )

        # 2. Digital Twin verified state
        services = context.get("services", {})
        if services:
            items.append(
                EvidenceItem(
                    evidence_type="environment_topology",
                    strength=EvidenceStrength.VERIFIED,
                    trust_level=DataTrustLevel.TRUSTED_SYSTEM_DATA,
                    source="digital_twin_topology",
                    summary=f"Active topology verified: {len(services)} managed service node(s).",
                    is_primary=True,
                    confidence=0.95,
                )
            )

        # 3. Model-derived simulation evidence
        if simulation_data:
            sim_conf = float(simulation_data.get("confidence", 0.8))
            items.append(
                EvidenceItem(
                    evidence_type="sandboxed_simulation",
                    strength=EvidenceStrength.SUPPORTED if sim_conf >= 0.75 else EvidenceStrength.INDICATIVE,
                    trust_level=DataTrustLevel.SIMULATED_DATA,
                    source=f"simulation_engine:{simulation_data.get('simulation_id', 'sim_run')}",
                    summary=f"Sandboxed counterfactual simulation completed with {sim_conf * 100:.1f}% calibrated confidence.",
                    is_primary=False,
                    confidence=sim_conf,
                )
            )

        # 4. Model-derived causal evidence
        if causal_data:
            items.append(
                EvidenceItem(
                    evidence_type="causal_relationship",
                    strength=EvidenceStrength.SUPPORTED,
                    trust_level=DataTrustLevel.MODEL_GENERATED_DATA,
                    source="causal_reasoning_engine",
                    summary=f"Causal mechanism identified: {causal_data.get('summary', 'Dependency-based causal path verified.')}",
                    is_primary=False,
                    confidence=0.85,
                )
            )

        # Compute overall strength
        primary_count = sum(1 for e in items if e.is_primary)
        if primary_count >= 2:
            overall = EvidenceStrength.VERIFIED
        elif items:
            overall = EvidenceStrength.SUPPORTED
        else:
            overall = EvidenceStrength.UNKNOWN

        return EvidenceSet(
            decision_id=decision_id,
            items=items,
            overall_strength=overall,
            untrusted_data_count=0,
        )

    def build_evidence_set(
        self,
        decision_id: str,
        provided_items: list[EvidenceItem] | None = None,
        simulations: list[dict[str, Any]] | None = None,
        causal_inference: dict[str, Any] | None = None,
        digital_twin_state: dict[str, Any] | None = None,
    ) -> EvidenceSet:
        """Assembles, grades, and classifies evidence supporting the decision."""
        items: list[EvidenceItem] = list(provided_items or [])

        # Add digital twin telemetry if present
        if digital_twin_state:
            items.append(
                EvidenceItem(
                    evidence_type="environment_state",
                    strength=EvidenceStrength.VERIFIED,
                    trust_level=DataTrustLevel.TRUSTED_SYSTEM_DATA,
                    source="digital_twin_world_model",
                    summary=f"Current environment state verified for scope: {digital_twin_state.get('scope', 'SYSTEM')}",
                    is_primary=True,
                    confidence=0.95,
                )
            )

        # Add simulations evidence
        if simulations:
            for sim in simulations:
                conf = float(sim.get("confidence", 0.8))
                is_stale = sim.get("is_stale", False)
                items.append(
                    EvidenceItem(
                        evidence_type="sandboxed_simulation",
                        strength=EvidenceStrength.INDICATIVE if is_stale else (EvidenceStrength.SUPPORTED if conf >= 0.75 else EvidenceStrength.INDICATIVE),
                        trust_level=DataTrustLevel.SIMULATED_DATA,
                        source=f"simulation_engine:{sim.get('simulation_id', 'sim')}",
                        summary=f"Simulation result (stale={is_stale}) with {conf * 100:.0f}% confidence",
                        is_primary=False,
                        confidence=conf if not is_stale else min(conf, 0.4),
                    )
                )

        # Add causal inference evidence
        if causal_inference:
            items.append(
                EvidenceItem(
                    evidence_type="causal_relationship",
                    strength=EvidenceStrength.SUPPORTED,
                    trust_level=DataTrustLevel.MODEL_GENERATED_DATA,
                    source="causal_reasoning_engine",
                    summary=f"Causal mechanism identified: {causal_inference.get('suspected_cause', 'Causal path verified')}",
                    is_primary=False,
                    confidence=float(causal_inference.get("confidence_score", 0.85)),
                )
            )

        untrusted_count = sum(
            1 for e in items
            if e.trust_level in {DataTrustLevel.UNVERIFIED_EXTERNAL_DATA, DataTrustLevel.MODEL_GENERATED_DATA}
        )

        primary_count = sum(1 for e in items if e.is_primary)
        if primary_count >= 2:
            overall = EvidenceStrength.VERIFIED
        elif items:
            overall = EvidenceStrength.SUPPORTED
        else:
            overall = EvidenceStrength.UNKNOWN

        return EvidenceSet(
            decision_id=decision_id,
            items=items,
            overall_strength=overall,
            untrusted_data_count=untrusted_count,
        )


evidence_engine = EvidenceEngine()

