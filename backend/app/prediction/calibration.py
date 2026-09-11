"""Probability Calibration, Brier Score, Small-Sample Uncertainty, and Learning Feedback Loop (Task 47)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import logging
import math
from typing import Any, Dict, List, Optional
import uuid

logger = logging.getLogger("kairo.prediction.calibration")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class OutcomeType(str, Enum):
    """Evaluation outcome classification (Spec 22, 142)."""

    CORRECT = "CORRECT"
    INCORRECT = "INCORRECT"
    PARTIALLY_CORRECT = "PARTIALLY_CORRECT"
    EXPIRED = "EXPIRED"
    UNKNOWN = "UNKNOWN"


@dataclass
class OutcomeRecord:
    """Historical outcome record linking predicted probability with realized state (Spec 19-24)."""

    predicted_prob: float
    actual_outcome: Optional[int]
    outcome_type: OutcomeType
    prediction_id: Optional[str] = None
    intervened: bool = False
    intervention_details: Optional[str] = None
    recorded_at: datetime = field(default_factory=utc_now)


@dataclass
class CalibrationBucket:
    """Decile probability bucket for calibration curve analysis (Spec 14)."""

    bin_lower: float
    bin_upper: float
    count: int = 0
    avg_predicted_prob: float = 0.0
    empirical_rate: float = 0.0
    calibration_gap: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bin_range": f"{self.bin_lower:.1f}-{self.bin_upper:.1f}",
            "count": self.count,
            "avg_predicted_prob": round(self.avg_predicted_prob, 4),
            "empirical_rate": round(self.empirical_rate, 4),
            "calibration_gap": round(self.calibration_gap, 4),
        }


@dataclass
class CalibrationMetrics:
    """Statistical calibration metrics tracking forecast accuracy (Spec 14, 19, 20)."""

    model_reference: str = "default_model"
    sample_size: int = 0
    brier_score: float = 0.25  # (f - o)^2, where 0 is perfect calibration
    log_loss: float = 0.693
    calibration_error: float = 0.5
    accuracy: float = 0.5
    expected_calibration_error: float = 0.0
    maximum_calibration_error: float = 0.0
    buckets: List[CalibrationBucket] = field(default_factory=list)
    systematic_bias: str = "BALANCED"  # OVERCONFIDENT, UNDERCONFIDENT, BALANCED
    is_degraded: bool = False
    last_evaluated_at: datetime = field(default_factory=utc_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_reference": self.model_reference,
            "sample_size": self.sample_size,
            "brier_score": round(self.brier_score, 4),
            "log_loss": round(self.log_loss, 4),
            "calibration_error": round(self.calibration_error, 4),
            "accuracy": round(self.accuracy, 4),
            "expected_calibration_error": round(self.expected_calibration_error, 4),
            "maximum_calibration_error": round(self.maximum_calibration_error, 4),
            "buckets": [b.to_dict() for b in self.buckets],
            "systematic_bias": self.systematic_bias,
            "is_degraded": self.is_degraded,
            "last_evaluated_at": self.last_evaluated_at.isoformat(),
        }


class ProbabilityCalibrator:
    """Evaluates prediction probabilities against observed reality and tunes confidence (Spec 17-23, 110)."""

    def __init__(
        self,
        min_sample_threshold: int = 10,
        min_sample_size: int = 10,
        model_reference: str = "default_model",
    ) -> None:
        self.model_reference = model_reference
        self.min_sample_size = max(min_sample_threshold, min_sample_size)
        self._records: List[OutcomeRecord] = []
        # model_ref -> list of (predicted_prob 0.0-1.0, actual_outcome 0 or 1, action_influenced bool)
        self._history: Dict[str, List[tuple[float, int, bool]]] = {}

    def record(
        self,
        prediction_probability: float,
        actual_outcome: int,
        action_influenced: bool = False,
        model_reference: Optional[str] = None,
    ) -> None:
        ref = model_reference or self.model_reference
        self.record_outcome(
            predicted_prob=prediction_probability,
            actual_outcome=actual_outcome,
            model_reference=ref,
            action_influenced=action_influenced,
        )

    def evaluate_calibration(self, model_reference: Optional[str] = None) -> CalibrationMetrics:
        ref = model_reference or self.model_reference
        return self.compute_metrics(model_reference=ref)

    def record_outcome(
        self,
        predicted_prob: Any = None,
        actual_outcome: Any = None,
        outcome_type: OutcomeType = OutcomeType.CORRECT,
        prediction_id: Optional[str] = None,
        intervened: bool = False,
        intervention_details: Optional[str] = None,
        model_reference: str = "default_model",
        action_influenced: bool = False,
        **kwargs: Any,
    ) -> None:
        """Enforce Spec 23, 24: Record outcome for calibration; flag if Kairo action influenced outcome."""
        if predicted_prob is None:
            predicted_prob = kwargs.get("predicted_probability") or kwargs.get("probability") or 0.5
        if actual_outcome is None and "actual_occurred" in kwargs:
            actual_outcome = kwargs["actual_occurred"]
        if "model_reference" in kwargs:
            model_reference = kwargs["model_reference"]
        if "action_influenced" in kwargs:
            action_influenced = kwargs["action_influenced"]
        # Handle positional / keyword call styles
        if isinstance(predicted_prob, str) and not isinstance(actual_outcome, (int, float, type(None))):
            # Signature: record_outcome(model_reference, predicted_probability, actual_occurred, action_influenced)
            model_ref = predicted_prob
            prob = float(actual_outcome)
            actual_bool = bool(outcome_type)
            act_inf = bool(prediction_id) if prediction_id is not None else action_influenced
            outcome_val = 1 if actual_bool else 0
            self._history.setdefault(model_ref, []).append((prob, outcome_val, act_inf))
            rec = OutcomeRecord(
                predicted_prob=prob,
                actual_outcome=outcome_val,
                outcome_type=OutcomeType.CORRECT if actual_bool else OutcomeType.INCORRECT,
                prediction_id=None,
                intervened=act_inf,
                intervention_details=None,
            )
            self._records.append(rec)
            return

        prob = float(predicted_prob) if predicted_prob is not None else 0.5
        act_val = int(actual_outcome) if actual_outcome is not None else None
        inf = intervened or action_influenced

        rec = OutcomeRecord(
            predicted_prob=prob,
            actual_outcome=act_val,
            outcome_type=outcome_type,
            prediction_id=prediction_id,
            intervened=inf,
            intervention_details=intervention_details,
        )
        self._records.append(rec)

        if act_val is not None:
            self._history.setdefault(model_reference, []).append((prob, act_val, inf))

    def get_records(self) -> List[OutcomeRecord]:
        return list(self._records)

    def compute_brier_score(self) -> Optional[float]:
        # Filter out unknown or intervened outcomes to prevent outcome bias (Spec 24, 143)
        valid = [r for r in self._records if r.actual_outcome is not None and not r.intervened]
        if not valid:
            return None
        return sum((r.predicted_prob - r.actual_outcome) ** 2 for r in valid) / len(valid)

    def compute_metrics(self, model_reference: str = "default_model") -> CalibrationMetrics:
        return self.compute_calibration(model_reference)

    def compute_calibration(self, model_reference: str = "default_model") -> CalibrationMetrics:
        """Enforce Spec 19-21: Compute Brier score and log loss.
        Small sample size must reduce confidence or increase uncertainty (Spec 21).
        """
        valid = [r for r in self._records if r.actual_outcome is not None and not r.intervened]
        if not valid:
            records = self._history.get(model_reference, [])
            clean_records = [r for r in records if not r[2]]
        else:
            clean_records = [(r.predicted_prob, r.actual_outcome, r.intervened) for r in valid]

        if not clean_records:
            return CalibrationMetrics(
                model_reference=model_reference,
                sample_size=0,
                brier_score=0.25,
                log_loss=0.693,
                calibration_error=0.5,
                accuracy=0.5,
            )

        n = len(clean_records)
        brier_sum = sum((prob - actual) ** 2 for prob, actual, _ in clean_records)
        brier_score = brier_sum / n

        eps = 1e-15
        log_loss_sum = sum(
            -(actual * math.log(max(eps, min(1 - eps, prob))) + (1 - actual) * math.log(max(eps, min(1 - eps, 1 - prob))))
            for prob, actual, _ in clean_records
        )
        log_loss = log_loss_sum / n

        correct_count = sum(1 for prob, actual, _ in clean_records if (prob >= 0.5 and actual == 1) or (prob < 0.5 and actual == 0))
        accuracy = correct_count / n

        calib_err = abs((sum(p for p, _, _ in clean_records) / n) - (sum(a for _, a, _ in clean_records) / n))

        # Enforce Spec 21: Small sample penalty
        if n < self.min_sample_size:
            penalty = (self.min_sample_size - n) / (self.min_sample_size * 2.0)
            calib_err = min(1.0, calib_err + penalty)

        # Compute Decile Calibration Buckets (Spec 14)
        buckets: List[CalibrationBucket] = []
        ece_sum = 0.0
        mce_val = 0.0
        num_bins = 10

        for b in range(num_bins):
            b_low = b / num_bins
            b_high = (b + 1) / num_bins
            # Include upper bound in last bin
            if b == num_bins - 1:
                in_bin = [(p, a) for p, a, _ in clean_records if b_low <= p <= b_high]
            else:
                in_bin = [(p, a) for p, a, _ in clean_records if b_low <= p < b_high]

            b_count = len(in_bin)
            if b_count > 0:
                avg_p = sum(p for p, _ in in_bin) / b_count
                emp_r = sum(a for _, a in in_bin) / b_count
                gap = abs(avg_p - emp_r)
                ece_sum += (b_count / n) * gap
                mce_val = max(mce_val, gap)
            else:
                avg_p = (b_low + b_high) / 2.0
                emp_r = 0.0
                gap = 0.0

            buckets.append(
                CalibrationBucket(
                    bin_lower=b_low,
                    bin_upper=b_high,
                    count=b_count,
                    avg_predicted_prob=avg_p,
                    empirical_rate=emp_r,
                    calibration_gap=gap,
                )
            )

        # Detect systematic bias
        mean_p = sum(p for p, _, _ in clean_records) / n
        mean_a = sum(a for _, a, _ in clean_records) / n
        bias_delta = mean_p - mean_a
        if bias_delta > 0.05:
            systematic_bias = "OVERCONFIDENT"
        elif bias_delta < -0.05:
            systematic_bias = "UNDERCONFIDENT"
        else:
            systematic_bias = "BALANCED"

        # Model degradation check (Spec 14)
        is_degraded = n >= self.min_sample_size and (ece_sum > 0.20 or brier_score > 0.25)

        return CalibrationMetrics(
            model_reference=model_reference,
            sample_size=n,
            brier_score=brier_score,
            log_loss=log_loss,
            calibration_error=calib_err,
            accuracy=accuracy,
            expected_calibration_error=ece_sum,
            maximum_calibration_error=mce_val,
            buckets=buckets,
            systematic_bias=systematic_bias,
            is_degraded=is_degraded,
        )

    def calibrate_confidence(self, raw_confidence: float, domain: str = "") -> tuple[float, float]:
        """Calibrate raw confidence and return (adjusted_confidence, uncertainty)."""
        valid = [r for r in self._records if r.actual_outcome is not None and not r.intervened]
        n = len(valid)
        if n < self.min_sample_size:
            shrinkage = (self.min_sample_size - n) / float(self.min_sample_size)
            calibrated = (raw_confidence * (1.0 - shrinkage)) + (0.5 * shrinkage)
            uncertainty = min(0.9, 0.2 + (shrinkage * 0.5))
            return round(calibrated, 3), round(uncertainty, 3)
        return round(raw_confidence, 3), 0.1

    def adjust_confidence_for_sample_size(self, raw_confidence: float, model_reference: str) -> float:
        records = self._history.get(model_reference, [])
        n = len([r for r in records if not r[2]])
        if n < self.min_sample_size:
            shrinkage = (self.min_sample_size - n) / float(self.min_sample_size)
            adjusted = (raw_confidence * (1.0 - shrinkage)) + (0.5 * shrinkage)
            return round(adjusted, 3)
        return round(raw_confidence, 3)
