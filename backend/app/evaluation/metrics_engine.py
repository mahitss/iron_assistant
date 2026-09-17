"""Metrics Framework, Probabilistic Calibration (ECE/Brier) & Statistical Discipline.
Task 104 Section 6 & 50.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple
from app.evaluation.domain import GateStatus, MetricMeasurement, MetricType


class StatisticalMetricsCalculator:
    """Calculates typed metrics with statistical rigor and confidence intervals."""

    MIN_SAMPLE_SIZE_DEFAULT = 5
    MIN_SAMPLE_SIZE_REGRESSION = 10

    @classmethod
    def compute_accuracy_precision_recall_f1(
        cls, tp: int, fp: int, tn: int, fn: int
    ) -> dict[str, float]:
        """Calculates classification metrics from confusion matrix."""
        total = tp + fp + tn + fn
        if total == 0:
            return {"accuracy": 0.0, "precision": 0.0, "recall": 0.0, "f1": 0.0}

        accuracy = (tp + tn) / total
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
        fnr = fn / (fn + tp) if (fn + tp) > 0 else 0.0

        return {
            "accuracy": round(accuracy, 4),
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "false_positive_rate": round(fpr, 4),
            "false_negative_rate": round(fnr, 4),
        }

    @classmethod
    def compute_brier_score(cls, predictions: list[float], outcomes: list[int | bool]) -> float:
        """Computes Brier Score: 1/N * sum((predicted_prob - actual_outcome)^2).
        Lower is better (0 is perfect calibration, 1 is total error).
        """
        if not predictions or not outcomes or len(predictions) != len(outcomes):
            return 0.0
        n = len(predictions)
        total_sq_err = sum((float(p) - (1.0 if o else 0.0)) ** 2 for p, o in zip(predictions, outcomes))
        return round(total_sq_err / n, 4)

    @classmethod
    def compute_expected_calibration_error(
        cls, predictions: list[float], outcomes: list[int | bool], num_bins: int = 10
    ) -> float:
        """Computes Expected Calibration Error (ECE) across confidence bins."""
        if not predictions or not outcomes or len(predictions) != len(outcomes):
            return 0.0

        n = len(predictions)
        bin_boundaries = [i / num_bins for i in range(num_bins + 1)]
        ece = 0.0

        for i in range(num_bins):
            bin_lower = bin_boundaries[i]
            bin_upper = bin_boundaries[i + 1]

            bin_preds: list[float] = []
            bin_actuals: list[float] = []

            for p, o in zip(predictions, outcomes):
                p_val = float(p)
                o_val = 1.0 if o else 0.0
                if (i == 0 and bin_lower <= p_val <= bin_upper) or (bin_lower < p_val <= bin_upper):
                    bin_preds.append(p_val)
                    bin_actuals.append(o_val)

            if bin_preds:
                bin_size = len(bin_preds)
                avg_confidence = sum(bin_preds) / bin_size
                avg_accuracy = sum(bin_actuals) / bin_size
                ece += (bin_size / n) * abs(avg_accuracy - avg_confidence)

        return round(ece, 4)

    @classmethod
    def compute_confidence_interval(
        cls, successes: int, total: int, confidence: float = 0.95
    ) -> tuple[float, float]:
        """Wilson score interval for binomial proportions."""
        if total == 0:
            return 0.0, 0.0

        # Normal critical value approx for 95% is 1.96
        z = 1.96 if confidence >= 0.95 else 1.645
        p_hat = successes / total
        denominator = 1 + (z**2) / total
        centre = p_hat + (z**2) / (2 * total)
        spread = z * math.sqrt((p_hat * (1 - p_hat) + (z**2) / (4 * total)) / total)

        low = max(0.0, (centre - spread) / denominator)
        high = min(1.0, (centre + spread) / denominator)
        return round(low, 4), round(high, 4)

    @classmethod
    def evaluate_measurement(
        cls,
        run_id: str,
        metric_name: str,
        metric_type: MetricType,
        values: list[float],
        threshold: Optional[float] = None,
        direction: str = "HIGHER_IS_BETTER",
        min_sample_size: int = MIN_SAMPLE_SIZE_DEFAULT,
    ) -> MetricMeasurement:
        """Evaluates a metric sample with strict sample size discipline (Section 50).
        If sample count is below minimum, status is INCONCLUSIVE, NEVER PASS!
        """
        sample_size = len(values)
        if sample_size == 0:
            return MetricMeasurement(
                run_id=run_id,
                metric_name=metric_name,
                metric_type=metric_type,
                value=0.0,
                sample_size=0,
                status=GateStatus.INCONCLUSIVE,
                threshold=threshold,
                direction=direction,
            )

        mean_val = sum(values) / sample_size
        variance = (sum((v - mean_val) ** 2 for v in values) / (sample_size - 1)) if sample_size > 1 else 0.0

        # Insufficient sample size check -> INCONCLUSIVE
        if sample_size < min_sample_size:
            return MetricMeasurement(
                run_id=run_id,
                metric_name=metric_name,
                metric_type=metric_type,
                value=round(mean_val, 4),
                sample_size=sample_size,
                variance=round(variance, 4),
                status=GateStatus.INCONCLUSIVE,
                threshold=threshold,
                direction=direction,
            )

        # Confidence Interval (Student-t or normal approx)
        margin = 1.96 * math.sqrt(variance / sample_size) if sample_size > 1 else 0.0
        ci_low = round(mean_val - margin, 4)
        ci_high = round(mean_val + margin, 4)

        status = GateStatus.PASS
        if threshold is not None:
            if direction == "HIGHER_IS_BETTER":
                status = GateStatus.PASS if mean_val >= threshold else GateStatus.FAIL
            elif direction == "LOWER_IS_BETTER":
                status = GateStatus.PASS if mean_val <= threshold else GateStatus.FAIL

        return MetricMeasurement(
            run_id=run_id,
            metric_name=metric_name,
            metric_type=metric_type,
            value=round(mean_val, 4),
            sample_size=sample_size,
            confidence_interval_low=ci_low,
            confidence_interval_high=ci_high,
            variance=round(variance, 4),
            status=status,
            threshold=threshold,
            direction=direction,
        )


class SubsystemMetricsScorer:
    """Specialized scoring distinguishing factual correctness vs retrieval relevance,
    execution success vs outcome success, and consensus vs truth.
    """

    @classmethod
    def score_memory_retrieval(
        cls, retrieved_facts: list[str], expected_facts: list[str], ground_truth_validity: dict[str, bool]
    ) -> dict[str, float]:
        """Calculates both retrieval relevance AND factual correctness.
        Crucial: A retrieval can be highly semantically relevant but factually false!
        """
        if not retrieved_facts:
            return {"retrieval_relevance": 0.0, "factual_correctness": 0.0, "stale_memory_ratio": 0.0}

        relevant_count = sum(1 for f in retrieved_facts if any(e.lower() in f.lower() for e in expected_facts))
        relevance = relevant_count / len(retrieved_facts)

        correct_count = sum(1 for f in retrieved_facts if ground_truth_validity.get(f, True))
        factual_correctness = correct_count / len(retrieved_facts)

        stale_count = sum(1 for f in retrieved_facts if not ground_truth_validity.get(f, True))
        stale_ratio = stale_count / len(retrieved_facts)

        return {
            "retrieval_relevance": round(relevance, 4),
            "factual_correctness": round(factual_correctness, 4),
            "stale_memory_ratio": round(stale_ratio, 4),
        }

    @classmethod
    def score_action_execution(
        cls, preflight_ok: bool, executed: bool, postconditions_satisfied: bool, rollback_succeeded: bool = False
    ) -> dict[str, Any]:
        """Evaluates execution_success vs outcome_success (Section 12)."""
        execution_success = executed
        outcome_success = preflight_ok and executed and postconditions_satisfied

        return {
            "execution_success": execution_success,
            "outcome_success": outcome_success,
            "postconditions_satisfied": postconditions_satisfied,
            "rollback_success": rollback_succeeded if not outcome_success else True,
            "passed": outcome_success,
        }

    @classmethod
    def score_self_model_readiness(
        cls, predicted_readiness: bool, actual_readiness: bool
    ) -> tuple[bool, float]:
        """Evaluates whether self-model capability readiness prediction matched reality (Section 16)."""
        error = 0.0 if predicted_readiness == actual_readiness else 1.0
        is_accurate = predicted_readiness == actual_readiness
        return is_accurate, error

    @classmethod
    def score_multi_agent_consensus(
        cls, agent_opinions: list[str], ground_truth: str
    ) -> dict[str, float]:
        """Evaluates consensus vs ground truth (Section 18).
        Never equate consensus with truth!
        """
        if not agent_opinions:
            return {"agreement_rate": 0.0, "ground_truth_accuracy": 0.0}

        majority = max(set(agent_opinions), key=agent_opinions.count)
        agreement_rate = agent_opinions.count(majority) / len(agent_opinions)
        truth_accuracy = 1.0 if majority.strip().lower() == ground_truth.strip().lower() else 0.0

        return {
            "agent_agreement": round(agreement_rate, 4),
            "ground_truth_accuracy": round(truth_accuracy, 4),
            "consensus_matches_truth": 1.0 if (agreement_rate >= 0.6 and truth_accuracy == 1.0) else 0.0,
        }
