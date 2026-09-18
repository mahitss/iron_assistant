"""Autonomous Evidence Evaluation and Independence Engine (Task 115 Section 15, 16, 17, 18, 19, 45).

Evaluates incoming evidence against hypotheses, enforces evidence independence lineage,
prevents echo-chamber inflation from derived or duplicate signals, updates multi-dimensional
confidence profiles, and adjusts hypothesis lifecycle states.

Hard Invariants:
- AGENT CLAIM != INDEPENDENT EVIDENCE
- Telemetry A -> Derived signal B -> Agent C report does NOT equal 3 independent evidence items.
- Absence of evidence != Evidence of absence (missing telemetry != negative evidence).
- Simulation / Counterfactual evidence remains strictly tagged and cannot masquerade as real-world proof.
- Updates multi-dimensional confidence profile; does NOT collapse into an arbitrary opaque scalar.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List

from app.hypothesis.domain import (
    EvidenceIndependence,
    EvidenceType,
    Hypothesis,
    HypothesisEvidenceAssessment,
    HypothesisEvidenceItem,
    HypothesisStatus,
    SupportVerdict,
)

logger = logging.getLogger("kairo.hypothesis.evidence")


class EvidenceEvaluator:
    """Evaluates evidence items against candidate hypotheses with strict independence tracking."""

    def assess_independence(
        self,
        item: HypothesisEvidenceItem,
        existing_evidence: List[HypothesisEvidenceItem],
    ) -> EvidenceIndependence:
        """Determines whether a piece of evidence is truly independent, derived, duplicate, or correlated."""
        # 1. If explicit parent IDs are provided, it is derived
        if item.parent_evidence_ids:
            return EvidenceIndependence.DERIVED

        # 2. Check for duplicate payload content or exact same source telemetry
        for ex in existing_evidence:
            if ex.evidence_id == item.evidence_id:
                continue

            # Same source and identical key values within a 5-second window
            if ex.source == item.source and ex.evidence_type == item.evidence_type:
                time_diff = abs((item.timestamp - ex.timestamp).total_seconds())
                if time_diff < 5.0 and ex.payload == item.payload:
                    return EvidenceIndependence.DUPLICATE

            # Agent repeating derived telemetry
            if (
                item.evidence_type in (EvidenceType.AGENT_REPORT, EvidenceType.USER_REPORT)
                and ex.evidence_type in (EvidenceType.TELEMETRY, EvidenceType.OBSERVATION)
            ):
                m_name = item.payload.get("metric_name")
                o_val = item.payload.get("observed_value")
                if m_name and (
                    ex.payload.get(m_name) == o_val
                    or (ex.payload.get("metric_name") == m_name and ex.payload.get("observed_value") == o_val)
                ):
                    return EvidenceIndependence.DERIVED

            # Correlated signals from same cluster/subsystem at exact same second
            if (
                item.source_type == ex.source_type
                and item.source == ex.source
                and abs((item.timestamp - ex.timestamp).total_seconds()) < 1.0
            ):
                return EvidenceIndependence.CORRELATED

        return EvidenceIndependence.INDEPENDENT

    def evaluate_evidence_against_hypothesis(
        self,
        hyp: Hypothesis,
        evidence: HypothesisEvidenceItem,
        existing_evidence: List[HypothesisEvidenceItem],
    ) -> HypothesisEvidenceAssessment:
        """Assesses how an evidence item relates to a specific hypothesis."""
        # Re-verify independence against existing evidence corpus
        independence = self.assess_independence(evidence, existing_evidence)
        evidence.independence = independence

        target_metric = hyp.claim.target_metric
        payload = evidence.payload

        verdict = SupportVerdict.NEUTRAL
        reasoning = "Evidence does not directly inform this hypothesis claim."
        confidence = 0.5
        temporal_fit = 0.8
        causal_fit = 0.7

        # Check for Falsification conditions match
        for f_cond in hyp.falsification_conditions:
            for req_obs in f_cond.required_observations:
                if req_obs in str(evidence.source) or req_obs in str(payload):
                    # Check metric thresholds
                    for metric, max_val in f_cond.metric_thresholds.items():
                        if metric in payload and float(payload[metric]) <= float(max_val):
                            verdict = SupportVerdict.FALSIFIES
                            reasoning = f"Observation {metric}={payload[metric]} satisfies falsification condition: {f_cond.description}"
                            f_cond.is_falsified = True
                            f_cond.falsification_evidence_ids.append(evidence.evidence_id)
                            f_cond.falsification_reasoning = reasoning
                            break
            if verdict == SupportVerdict.FALSIFIES:
                break

        if verdict != SupportVerdict.FALSIFIES:
            # Check predictive or metric alignment
            if target_metric and target_metric in payload:
                val = float(payload[target_metric])
                direction = hyp.claim.expected_direction

                if direction == "increase":
                    if val > 80.0 or payload.get("anomaly") is True:
                        verdict = SupportVerdict.SUPPORTS
                        reasoning = f"Elevated metric {target_metric}={val} aligns with hypothesis prediction."
                        confidence = 0.85 if independence == EvidenceIndependence.INDEPENDENT else 0.65
                    elif val < 40.0:
                        # Negative evidence: metric is distinctly normal
                        verdict = SupportVerdict.CONTRADICTS
                        reasoning = f"Low metric {target_metric}={val} directly contradicts expected saturation."
                        confidence = 0.80
                elif direction == "decrease":
                    if val < 20.0 or payload.get("anomaly") is True:
                        verdict = SupportVerdict.SUPPORTS
                        reasoning = f"Depressed metric {target_metric}={val} supports hypothesis."
                        confidence = 0.85 if independence == EvidenceIndependence.INDEPENDENT else 0.65
                    elif val > 60.0:
                        verdict = SupportVerdict.CONTRADICTS
                        reasoning = f"Metric {target_metric}={val} contradicts expected decline."
                        confidence = 0.80

            # Check matching contradiction signals
            for f_cond in hyp.falsification_conditions:
                for sig in f_cond.contradiction_signals:
                    if sig in payload or sig == payload.get("signal_name"):
                        verdict = SupportVerdict.WEAKLY_CONTRADICTS if verdict == SupportVerdict.NEUTRAL else verdict
                        reasoning = f"Contradiction signal detected: {sig}"

            # Check predictions matching
            for pred in hyp.predictions:
                if pred.expected_metric and pred.expected_metric in payload:
                    val = float(payload[pred.expected_metric])
                    pred.observed_outcome = val
                    if pred.expected_value_range:
                        low, high = pred.expected_value_range
                        if low <= val <= high:
                            pred.outcome_status = "CONFIRMED"
                            if verdict == SupportVerdict.NEUTRAL:
                                verdict = SupportVerdict.SUPPORTS
                                reasoning = f"Prediction {pred.predicted_event} confirmed with metric {val}"
                        else:
                            pred.outcome_status = "FAILED"
                            pred.failure_notes = f"Expected range [{low}, {high}] but observed {val}"
                            if verdict == SupportVerdict.NEUTRAL:
                                verdict = SupportVerdict.WEAKLY_CONTRADICTS
                                reasoning = f"Prediction failed: expected [{low}, {high}], got {val}"

        # Simulation or counterfactual weight discount
        if evidence.is_simulation or evidence.is_counterfactual:
            confidence *= 0.6  # strictly discounted
            reasoning += " [Note: Evidence derived from simulation/counterfactual model]"

        return HypothesisEvidenceAssessment(
            hypothesis_id=hyp.hypothesis_id,
            evidence_id=evidence.evidence_id,
            verdict=verdict,
            reasoning_basis=reasoning,
            confidence=round(confidence, 3),
            temporal_fit=temporal_fit,
            causal_fit=causal_fit,
            independence=independence,
        )

    def apply_assessment_to_hypothesis(
        self,
        hyp: Hypothesis,
        assessment: HypothesisEvidenceAssessment,
    ) -> None:
        """Updates hypothesis confidence profile and lifecycle status based on new assessment."""
        hyp.assessments.append(assessment)
        ev_id = assessment.evidence_id

        if assessment.verdict == SupportVerdict.FALSIFIES:
            if ev_id not in hyp.falsifying_evidence_ids:
                hyp.falsifying_evidence_ids.append(ev_id)
            hyp.status = HypothesisStatus.FALSIFIED
            hyp.confidence_profile.uncertainty = 0.05
            hyp.confidence_profile.contradiction_score = 1.0
            hyp.updated_at = datetime.now(timezone.utc)
            return

        if assessment.verdict in (SupportVerdict.SUPPORTS, SupportVerdict.WEAKLY_SUPPORTS):
            if ev_id not in hyp.supporting_evidence_ids:
                hyp.supporting_evidence_ids.append(ev_id)
        elif assessment.verdict in (SupportVerdict.CONTRADICTS, SupportVerdict.WEAKLY_CONTRADICTS):
            if ev_id not in hyp.contradicting_evidence_ids:
                hyp.contradicting_evidence_ids.append(ev_id)

        # Recalculate confidence profile dimensions
        self._recalculate_confidence_profile(hyp)

        # Update lifecycle state
        if hyp.status not in (HypothesisStatus.FALSIFIED, HypothesisStatus.REJECTED, HypothesisStatus.SUPERSEDED):
            if hyp.confidence_profile.contradiction_score >= 0.6:
                hyp.status = HypothesisStatus.CONTESTED
            elif hyp.confidence_profile.contradiction_score >= 0.3:
                hyp.status = HypothesisStatus.WEAKENED
            elif hyp.confidence_profile.evidence_strength >= 0.7 and hyp.confidence_profile.evidence_independence >= 0.5:
                # Advancing to STRONGLY_SUPPORTED requires contradiction search (handled by BiasGuardEngine)
                if hyp.contradiction_search_performed and hyp.confidence_profile.contradiction_score < 0.15:
                    hyp.status = HypothesisStatus.STRONGLY_SUPPORTED
                else:
                    hyp.status = HypothesisStatus.SUPPORTED
            elif hyp.confidence_profile.evidence_strength >= 0.3:
                hyp.status = HypothesisStatus.SUPPORTED
            else:
                hyp.status = HypothesisStatus.UNDER_INVESTIGATION

        hyp.updated_at = datetime.now(timezone.utc)

    def _recalculate_confidence_profile(self, hyp: Hypothesis) -> None:
        """Computes multidimensional confidence profile without hiding metrics."""
        assessments = hyp.assessments
        if not assessments:
            return

        support_scores: List[float] = []
        contradict_scores: List[float] = []
        independent_count = 0
        total_evidence = len(assessments)

        for a in assessments:
            if a.independence == EvidenceIndependence.INDEPENDENT:
                independent_count += 1

            if a.verdict == SupportVerdict.SUPPORTS:
                support_scores.append(a.confidence)
            elif a.verdict == SupportVerdict.WEAKLY_SUPPORTS:
                support_scores.append(a.confidence * 0.5)
            elif a.verdict == SupportVerdict.CONTRADICTS:
                contradict_scores.append(a.confidence)
            elif a.verdict == SupportVerdict.WEAKLY_CONTRADICTS:
                contradict_scores.append(a.confidence * 0.5)

        # Strength is average of supporting evidence weighted by count
        hyp.confidence_profile.evidence_strength = min(1.0, sum(support_scores) / (len(support_scores) or 1.0) * min(1.0, len(support_scores) * 0.4))
        # Independence is ratio of independent assessments to total
        hyp.confidence_profile.evidence_independence = round(independent_count / max(1, total_evidence), 3)
        # Contradiction score
        hyp.confidence_profile.contradiction_score = min(1.0, sum(contradict_scores) / (len(contradict_scores) or 1.0) * min(1.0, len(contradict_scores) * 0.5))

        # Predictive success
        confirmed = sum(1 for p in hyp.predictions if p.outcome_status == "CONFIRMED")
        failed = sum(1 for p in hyp.predictions if p.outcome_status == "FAILED")
        total_p = confirmed + failed
        if total_p > 0:
            hyp.confidence_profile.predictive_success = round(confirmed / total_p, 3)

        # Uncertainty drops with independent evidence, rises with contradictions
        raw_uncertainty = 1.0 - (0.5 * hyp.confidence_profile.evidence_strength + 0.3 * hyp.confidence_profile.evidence_independence)
        raw_uncertainty += 0.4 * hyp.confidence_profile.contradiction_score
        hyp.confidence_profile.uncertainty = max(0.05, min(1.0, raw_uncertainty))
