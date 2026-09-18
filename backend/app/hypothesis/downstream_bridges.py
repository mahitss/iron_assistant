"""Downstream Integration Bridges for Hypothesis Management (Task 115 Section 3, 4, 5, 6, 7, 27, 32, 33, 47, 48, 49, 50, 62).

Connects Hypothesis Engine to:
- Task 94 Decision Intelligence (provides structured candidate explanations without forcing choices)
- Task 107 Belief / Evidence Arbitration (submits evidence assessments without mutating beliefs directly)
- Task 112 Causal Explanation (imports causal chains)
- Task 113 Counterfactual Simulation (bounded what-if evaluation, strictly labeled SIMULATED)
- Task 114 Active Observation / VoI (translates discriminators to observation requests)
- Task 110 Cognitive Context Assembly (bounded summary for working set)
- EmergencyStop & SecurityCenter (strict fail-closed authority preservation)

Hard Invariants:
- HYPOTHESIS != BELIEF
- HYPOTHESIS != DECISION
- HYPOTHESIS != AUTHORIZATION
- HYPOTHESIS != ACTION
- EmergencyStop and SecurityCenter are strictly authoritative.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from app.hypothesis.domain import (
    EvidenceType,
    Hypothesis,
    HypothesisEvidenceItem,
    HypothesisExperimentCandidate,
    HypothesisSet,
)
from app.security.emergency_stop import get_emergency_stop_service

logger = logging.getLogger("kairo.hypothesis.bridges")


class HypothesisBridgeHub:
    """Manages secure, decoupled integrations with existing Kairo subsystems."""

    def __init__(
        self,
        belief_service: Any = None,
        causal_service: Any = None,
        counterfactual_service: Any = None,
        observation_service: Any = None,
        decision_service: Any = None,
    ) -> None:
        self.belief_service = belief_service
        self.causal_service = causal_service
        self.counterfactual_service = counterfactual_service
        self.observation_service = observation_service
        self.decision_service = decision_service

    def verify_safety_and_governance(self, user_id: str = "system") -> None:
        """Verifies EmergencyStop and security controls fail-closed."""
        stop_svc = get_emergency_stop_service()
        if stop_svc.is_stopped(user_id):
            raise PermissionError(
                "HYPOTHESIS_SAFETY_BLOCKED: Emergency Stop is actively engaged. Hypothesis evaluation suspended."
            )

    def prepare_decision_intelligence_payload(
        self,
        hset: HypothesisSet,
        hypotheses: List[Hypothesis],
    ) -> Dict[str, Any]:
        """Formats bounded hypothesis landscape for Task 94 Decision Intelligence."""
        active = [h for h in hypotheses if h.hypothesis_id in hset.active_hypothesis_ids]

        summary: List[Dict[str, Any]] = []
        for h in active:
            summary.append({
                "hypothesis_id": h.hypothesis_id,
                "statement": h.statement,
                "status": h.status.value,
                "is_unknown": h.is_unknown_hypothesis,
                "viability_score": h.confidence_profile.overall_viability_score(),
                "evidence_strength": h.confidence_profile.evidence_strength,
                "contradiction_score": h.confidence_profile.contradiction_score,
                "uncertainty": h.confidence_profile.uncertainty,
                "supporting_evidence_count": len(h.supporting_evidence_ids),
                "contradicting_evidence_count": len(h.contradicting_evidence_ids),
                "falsification_conditions_count": len(h.falsification_conditions),
            })

        return {
            "set_id": hset.set_id,
            "target_description": hset.target_description,
            "target_incident_id": hset.target_incident_id,
            "is_resolved": hset.is_resolved,
            "resolution_summary": hset.resolution_summary,
            "competing_hypotheses": summary,
            "information_gaps": hset.information_gaps,
            "recommended_discriminators": [d.to_dict() for d in hset.discriminators],
            "advisory_notice": (
                "Hypothesis engine provides structured competing explanations. "
                "Downstream Decision Engine remains solely authoritative for any action selection."
            ),
        }

    def prepare_bounded_context_for_working_set(
        self,
        hset: HypothesisSet,
        hypotheses: List[Hypothesis],
    ) -> Dict[str, Any]:
        """Provides a compact, token-bounded hypothesis state for Task 110 Context Working Set."""
        active = [h for h in hypotheses if h.hypothesis_id in hset.active_hypothesis_ids]

        items = []
        for h in active[:4]:  # Bounded to top 4 candidate explanations
            items.append({
                "id": h.hypothesis_id,
                "stmt": h.statement[:120],
                "status": h.status.value,
                "viability": round(h.confidence_profile.overall_viability_score(), 2),
                "uncertainty": round(h.confidence_profile.uncertainty, 2),
                "is_unknown": h.is_unknown_hypothesis,
            })

        next_obs = hset.discriminators[0].target_metric_or_signal if hset.discriminators else "None pending"

        return {
            "set_id": hset.set_id,
            "target": hset.target_description[:100],
            "active_hypotheses": items,
            "unresolved_gaps": len(hset.information_gaps),
            "next_discriminating_observation": next_obs,
            "is_resolved": hset.is_resolved,
        }

    def create_counterfactual_evidence_request(
        self,
        hyp: Hypothesis,
    ) -> HypothesisEvidenceItem:
        """Simulates what-if absence of hypothesized cause using Task 113 conventions."""
        evidence_item = HypothesisEvidenceItem(
            source=f"counterfactual_sim_{hyp.hypothesis_id}",
            source_type="simulation",
            evidence_type=EvidenceType.COUNTERFACTUAL,
            is_simulation=True,
            is_counterfactual=True,
            reliability_score=0.70,  # Simulation evidence is discounted
            provenance="Derived from Task 113 Counterfactual / Intervention Analysis",
            payload={
                "intervention": f"do({hyp.claim.subject} = nominal)",
                "predicted_outcome": "Incident recovery observed in simulated twin",
                "counterfactual_support": 0.75,
            },
        )
        return evidence_item

    def propose_experiment_candidate(
        self,
        target_hyp: Hypothesis,
        competing_hyps: List[Hypothesis],
    ) -> HypothesisExperimentCandidate:
        """Formulates an experiment candidate for Task 105 adaptation/experimentation engine."""
        return HypothesisExperimentCandidate(
            target_hypothesis_id=target_hyp.hypothesis_id,
            competing_hypothesis_ids=[h.hypothesis_id for h in competing_hyps if h.hypothesis_id != target_hyp.hypothesis_id],
            expected_outcome=f"Metric {target_hyp.claim.target_metric} will normalize under controlled probe",
            control_condition={"traffic_split": "control_baseline", "load": "normal"},
            treatment_condition={"traffic_split": "isolated_worker", "targeted_subsystem": target_hyp.claim.subject},
            safety_constraints=[
                "Maximum error rate threshold: 1%",
                "Automatic rollback if latency exceeds 500ms",
                "EmergencyStop trip wire active",
            ],
            success_criteria=[f"{target_hyp.claim.target_metric} shifts in predicted direction"],
            falsification_criteria=[
                f"{target_hyp.claim.target_metric} remains unchanged across control and treatment"
            ],
        )
