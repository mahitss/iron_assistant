"""Epistemic uncertainty quantification for Kairo Executive Decision Engine (Task 57).

Quantifies missing information, stale signals, and assumption counts.
Confidence must NOT simply equal the highest option score.
"""

from __future__ import annotations

from typing import Any

from app.decision.schemas import (
    CandidateOption,
    DecisionRequest,
    EvidenceSet,
    EvidenceStrength,
    UncertaintyAssessment,
)


class UncertaintyEngine:
    """Evaluates epistemic uncertainty and risk of false certainty."""

    def assess_uncertainty(
        self,
        request: DecisionRequest,
        options: list[CandidateOption],
        evidence_set: EvidenceSet,
        simulations: list[dict[str, Any]] | None = None,
        stale_environment: bool = False,
    ) -> UncertaintyAssessment:
        missing_data: list[str] = []
        stale_signals: list[str] = []
        assumptions_count = 0

        # Check for missing objectives or constraints
        if not request.objectives:
            missing_data.append("No explicit objectives defined; relying on generic defaults.")
            assumptions_count += 1
        if not request.constraints:
            missing_data.append("No hard or soft constraints specified.")

        # Check simulation freshness
        simulations = simulations or []
        for sim in simulations:
            if sim.get("is_stale"):
                stale_signals.append(f"Simulation {sim.get('simulation_id', 'unknown')} is stale or based on outdated state.")

        if stale_environment:
            stale_signals.append("Digital Twin environment model contains stale node states.")

        # Check option metrics completeness
        for opt in options:
            if not opt.metrics:
                missing_data.append(f"Option '{opt.name}' has no quantitative metrics; scoring relies on qualitative estimates.")
                assumptions_count += 1
            for k, v in opt.metrics.items():
                if v is None:
                    missing_data.append(f"Option '{opt.name}' has missing metric '{k}'.")

        # Evaluate evidence strength
        low_trust_evidence = sum(
            1 for ev in evidence_set.items
            if ev.strength in {EvidenceStrength.SPECULATIVE, EvidenceStrength.UNKNOWN}
        )
        if low_trust_evidence > 0:
            missing_data.append(f"{low_trust_evidence} evidence items are speculative or unknown.")

        # Calculate penalty-based confidence
        base_confidence = 0.95
        penalty = 0.0

        # Penalize for missing data
        penalty += min(0.40, len(missing_data) * 0.08)

        # Penalize for stale signals
        penalty += min(0.35, len(stale_signals) * 0.12)

        # Penalize for untrusted data
        penalty += min(0.20, evidence_set.untrusted_data_count * 0.05)

        computed_confidence = max(0.1, round(base_confidence - penalty, 2))

        # Determine qualitative uncertainty level
        if computed_confidence >= 0.80 and not stale_signals:
            overall = "LOW"
        elif computed_confidence >= 0.60:
            overall = "MEDIUM"
        elif computed_confidence >= 0.40:
            overall = "HIGH"
        else:
            overall = "CRITICAL"

        # If high-impact uncertainty exists or stale signals are critical, safe_to_proceed is False
        safe_to_proceed = overall not in {"CRITICAL"} and len(stale_signals) == 0

        return UncertaintyAssessment(
            overall_uncertainty=overall,
            confidence=computed_confidence,
            missing_data=missing_data,
            stale_signals=stale_signals,
            assumptions_count=assumptions_count,
            safe_to_proceed=safe_to_proceed,
        )


uncertainty_engine = UncertaintyEngine()
