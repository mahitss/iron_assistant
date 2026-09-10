"""Fallacy detection, causal evaluation metrics, benchmark tracking, and quality scoring (Task 55)."""

from __future__ import annotations

from typing import Any

from app.causal.schemas import (
    CausalEvidence,
    CausalExplanation,
    CausalGraph,
    EvidenceType,
    FallacyDetectionResult,
    FallacyType,
)


class CausalEvaluator:
    """Detects causal reasoning fallacies and evaluates explanation quality and benchmark accuracy."""

    @staticmethod
    def detect_fallacies(
        cause: str,
        effect: str,
        evidence: list[CausalEvidence],
        graph: CausalGraph | None = None,
        temporal_only: bool = False,
        known_common_ancestors: list[str] | None = None,
    ) -> FallacyDetectionResult:
        """Prompt #150, #151, #152, #153, #154: Explicitly audit for cognitive and statistical fallacies."""
        fallacies: list[FallacyType] = []
        reasons: list[str] = []

        # 1. Post Hoc Fallacy: Asserting cause purely because A preceded B
        if temporal_only or (evidence and all(ev.type == EvidenceType.OBSERVATION for ev in evidence)):
            fallacies.append(FallacyType.POST_HOC)
            reasons.append("Post hoc ergo propter hoc: Temporal precedence alone does not establish causation.")

        # 2. Common Cause Fallacy / Confounding
        if known_common_ancestors:
            fallacies.append(FallacyType.COMMON_CAUSE)
            fallacies.append(FallacyType.CONFOUNDING)
            reasons.append(
                f"Common upstream cause(s) detected: {known_common_ancestors}. "
                f"Apparent link between '{cause}' and '{effect}' may be confounded."
            )

        # 3. Reverse Causality Check
        if graph:
            # Check if there is already an edge going from effect -> cause
            for edge in graph.edges.values():
                if edge.cause == effect and edge.effect == cause:
                    fallacies.append(FallacyType.REVERSE_CAUSALITY)
                    reasons.append(f"Reverse path detected: '{effect}' is recorded as causing '{cause}'.")
                    break

        # 4. Selection Bias / Survivorship Bias
        if evidence and len(evidence) == 1 and evidence[0].type == EvidenceType.USER_REPORT:
            fallacies.append(FallacyType.SELECTION_BIAS)
            reasons.append("Selection bias: Reliance on a single unverified subjective report without telemetry baseline.")

        has_fallacy = len(fallacies) > 0
        rec = "Reject causal assertion until controlled experiment or independent mechanism evidence is provided." if has_fallacy else None

        return FallacyDetectionResult(
            has_fallacy=has_fallacy,
            fallacies=fallacies,
            reasons=reasons,
            recommendation=rec,
        )

    @staticmethod
    def evaluate_explanation_quality(explanation: CausalExplanation) -> dict[str, Any]:
        """Prompt #204: Measure evidence coverage, uncertainty calibration, and alternative coverage."""
        score = 0.0
        checks = {}

        # 1. What happened
        checks["has_what_happened"] = bool(explanation.what_happened)
        if checks["has_what_happened"]:
            score += 0.15

        # 2. Why it likely happened
        checks["has_why_mechanism"] = bool(explanation.why_it_likely_happened)
        if checks["has_why_mechanism"]:
            score += 0.20

        # 3. Evidence coverage
        checks["has_evidence"] = len(explanation.evidence_summary) > 0
        if checks["has_evidence"]:
            score += 0.20

        # 4. Alternatives considered
        checks["has_alternatives"] = len(explanation.alternatives) > 0
        if checks["has_alternatives"]:
            score += 0.20

        # 5. Uncertainty calibrated
        checks["has_uncertainty_stated"] = bool(explanation.uncertainty)
        if checks["has_uncertainty_stated"]:
            score += 0.15

        # 6. Test / Intervention plan
        checks["has_testing_plan"] = len(explanation.suggested_testing) > 0
        if checks["has_testing_plan"]:
            score += 0.10

        return {
            "overall_quality_score": round(score, 2),
            "is_comprehensive": score >= 0.85,
            "checklist": checks,
        }

    @staticmethod
    def calculate_benchmark_metrics(
        total_evaluations: int,
        verified_root_causes: int,
        false_discoveries: int,
        accurate_counterfactuals: int,
    ) -> dict[str, Any]:
        """Prompt #201-#207: Track accuracy, false discovery rate, and counterfactual precision."""
        fdr = (false_discoveries / total_evaluations) if total_evaluations > 0 else 0.0
        root_cause_accuracy = (verified_root_causes / total_evaluations) if total_evaluations > 0 else 0.0
        cf_precision = (accurate_counterfactuals / total_evaluations) if total_evaluations > 0 else 0.0

        return {
            "total_evaluations": total_evaluations,
            "root_cause_accuracy": round(root_cause_accuracy, 3),
            "false_discovery_rate": round(fdr, 3),
            "counterfactual_precision": round(cf_precision, 3),
            "status": "HEALTHY" if fdr <= 0.05 and root_cause_accuracy >= 0.80 else "DRIFT_DETECTED",
        }
