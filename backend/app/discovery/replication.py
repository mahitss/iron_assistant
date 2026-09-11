"""Experiment Replication, Conflict Detection, and Bias Auditing (Task 72).

Handles cross-run replication, detection of REPLICATION_CONFLICT when trials disagree,
and automated cognitive bias auditing (confirmation bias, selection bias, anchoring).
"""

from typing import Any

from app.discovery.schemas import (
    ExperimentResult,
)


class ReplicationEngine:
    """Manages replication studies and detects scientific conflicts without averaging out discrepancies."""

    def evaluate_replication(
        self,
        original_result: ExperimentResult,
        replication_result: ExperimentResult,
    ) -> dict[str, Any]:
        """Compares original trial with replication trial.

        Strict Principle: If replication disagrees, do NOT silently average results.
        Mark REPLICATION_CONFLICT and investigate.
        """
        is_consistent = (
            original_result.outcome == replication_result.outcome
            and original_result.is_valid
            and replication_result.is_valid
        )

        status = "REPLICATED" if is_consistent else "REPLICATION_CONFLICT"

        reasons: list[str] = []
        if not is_consistent:
            reasons.append(
                f"Outcome divergence: original trial concluded '{original_result.outcome.value}', "
                f"whereas replication concluded '{replication_result.outcome.value}'."
            )
            if not replication_result.is_valid:
                reasons.append(f"Replication invalidity: {replication_result.invalidation_reason}")

        # Update replication status in both results
        original_result.replication_status = status
        replication_result.replication_status = status

        return {
            "status": status,
            "original_experiment_id": original_result.experiment_id,
            "replication_experiment_id": replication_result.experiment_id,
            "is_consistent": is_consistent,
            "details": reasons or ["Replication confirmed original empirical findings."],
        }


class BiasDetector:
    """Audits discovery cycles for common cognitive and experimental biases."""

    def audit_biases(
        self,
        tested_hypotheses: list[dict[str, Any]],
        experiment_types_used: list[str],
        results: list[ExperimentResult],
    ) -> list[str]:
        """Detects potential biases in experimental design and hypothesis evaluation.

        Checks:
        1. Confirmation Bias: Were disconfirming tests skipped?
        2. Anchoring Bias: Was only the first generated hypothesis tested?
        3. Selection Bias: Were all experiments conducted in a single non-representative environment?
        """
        biases_detected: list[str] = []

        # 1. Anchoring / Order Bias check
        if len(tested_hypotheses) > 1:
            first_tested = tested_hypotheses[0]
            if first_tested.get("tested_first", False) and all(
                h.get("confidence", 0) < first_tested.get("confidence", 0) for h in tested_hypotheses[1:]
            ):
                biases_detected.append(
                    "Potential Anchoring Bias: First hypothesis selected was favored without proportional testing of alternatives."
                )

        # 2. Confirmation Bias check
        for h in tested_hypotheses:
            contra_count = len(h.get("contradicting_evidence", []))
            falsifiers_tested = h.get("falsification_tested", False)
            if contra_count == 0 and not falsifiers_tested:
                biases_detected.append(
                    f"Potential Confirmation Bias: Hypothesis '{h.get('hypothesis_id')}' was tested only for confirmation "
                    "without attempting active falsification."
                )

        # 3. Selection / Uniformity Bias check
        if experiment_types_used and len(set(experiment_types_used)) == 1 and len(experiment_types_used) > 3:
            biases_detected.append(
                f"Methodological Bias: Solely relied on '{experiment_types_used[0]}' trials without complementary investigation types."
            )

        return biases_detected


def calculate_sample_statistics(samples: list[float]) -> dict[str, float]:
    """Calculates factual sample statistics.

    Strict Principle: Do not claim statistical significance unless rigorous test passed.
    """
    if not samples:
        return {
            "sample_size": 0,
            "mean": 0.0,
            "median": 0.0,
            "variance": 0.0,
            "std_dev": 0.0,
        }

    n = len(samples)
    sorted_s = sorted(samples)
    mean_val = sum(samples) / n

    if n % 2 == 1:
        median_val = sorted_s[n // 2]
    else:
        median_val = (sorted_s[n // 2 - 1] + sorted_s[n // 2]) / 2.0

    variance_val = sum((x - mean_val) ** 2 for x in samples) / (n - 1) if n > 1 else 0.0
    std_dev_val = variance_val**0.5

    return {
        "sample_size": n,
        "mean": round(mean_val, 4),
        "median": round(median_val, 4),
        "variance": round(variance_val, 4),
        "std_dev": round(std_dev_val, 4),
    }
