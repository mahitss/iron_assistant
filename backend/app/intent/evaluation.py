"""Intent Evaluation Benchmarks, Error Taxonomy, and Calibration Metrics (Task 48)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("kairo.intent.evaluation")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class IntentErrorCategory(str, Enum):
    """Standardized error taxonomy for intent understanding failures (Spec 193)."""

    WRONG_INTENT = "WRONG_INTENT"
    WRONG_ENTITY = "WRONG_ENTITY"
    WRONG_SCOPE = "WRONG_SCOPE"
    WRONG_CONSTRAINT = "WRONG_CONSTRAINT"
    WRONG_DEADLINE = "WRONG_DEADLINE"
    WRONG_PREFERENCE = "WRONG_PREFERENCE"
    WRONG_INTERPRETATION = "WRONG_INTERPRETATION"


@dataclass
class EvaluationRecord:
    intent_id: str
    expected_intent_type: str
    predicted_intent_type: str
    is_correct: bool
    error_category: Optional[IntentErrorCategory] = None
    confidence: float = 1.0
    timestamp: datetime = field(default_factory=utc_now)


class IntentEvaluator:
    """Evaluates intent understanding benchmarks, tracks error taxonomy, and computes calibration (Spec 190-194)."""

    def __init__(self) -> None:
        self._records: List[EvaluationRecord] = []

    def record_evaluation(
        self,
        intent_id: str,
        expected: str,
        predicted: str,
        confidence: float = 1.0,
        error_category: Optional[IntentErrorCategory] = None,
    ) -> EvaluationRecord:
        correct = (expected.upper() == predicted.upper())
        rec = EvaluationRecord(
            intent_id=intent_id,
            expected_intent_type=expected,
            predicted_intent_type=predicted,
            is_correct=correct,
            error_category=None if correct else (error_category or IntentErrorCategory.WRONG_INTENT),
            confidence=confidence,
        )
        self._records.append(rec)
        return rec

    def compute_accuracy_metrics(self) -> Dict[str, Any]:
        """Enforce Spec 190: Track intent accuracy, error categories, and calibration."""
        if not self._records:
            return {
                "total_evaluations": 0,
                "accuracy": 1.0,
                "error_counts": {},
                "average_confidence": 1.0,
            }

        total = len(self._records)
        correct = sum(1 for r in self._records if r.is_correct)
        accuracy = round(correct / total, 3)

        error_counts: Dict[str, int] = {}
        for r in self._records:
            if not r.is_correct and r.error_category:
                cat = r.error_category.value
                error_counts[cat] = error_counts.get(cat, 0) + 1

        avg_conf = round(sum(r.confidence for r in self._records) / total, 3)

        return {
            "total_evaluations": total,
            "accuracy": accuracy,
            "error_counts": error_counts,
            "average_confidence": avg_conf,
        }
