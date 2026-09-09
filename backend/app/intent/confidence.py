"""Confidence Estimation, Scoring, and Calibration Against User Corrections (Tasks 35 & 48)."""

from __future__ import annotations

import logging
from typing import Dict, List, Optional
from app.intent.schemas import ResolutionMethod

logger = logging.getLogger("kairo.intent.confidence")


class ConfidenceEstimator:
    """Estimates interpretation and resolution confidence score (0.0 to 1.0) (Spec 63-66).
    
    CRITICAL INVARIANTS:
    1. Confidence != Authorization (Spec 64). High intent confidence does NOT authorize execution!
    2. Confidence != Truth (Spec 65). Intent confidence does not prove empirical facts.
    """

    BASE_SCORES = {
        ResolutionMethod.EXPLICIT: 1.0,
        ResolutionMethod.EXACT_MATCH: 0.98,
        ResolutionMethod.ALIAS: 0.88,
        ResolutionMethod.CONTEXT: 0.82,
        ResolutionMethod.FUZZY_MATCH: 0.60,
        ResolutionMethod.MODEL_INFERENCE: 0.65,
    }

    def __init__(self) -> None:
        self._corrections_count = 0
        self._confirmations_count = 0

    @classmethod
    def estimate(
        cls,
        resolution_methods: Optional[List[ResolutionMethod]] = None,
        has_ambiguity: bool = False,
        missing_params_count: int = 0,
        language_clarity_score: float = 1.0,
    ) -> float:
        """Calculates confidence strictly as an interpretation metric."""
        if not resolution_methods:
            base = 0.85
        else:
            scores = [cls.BASE_SCORES.get(m, 0.70) for m in resolution_methods]
            base = min(scores)

        base *= language_clarity_score

        # Penalize for ambiguity or missing required parameters
        if has_ambiguity:
            base *= 0.60

        if missing_params_count > 0:
            penalty = min(0.40, missing_params_count * 0.15)
            base -= penalty

        return round(max(0.10, min(1.0, base)), 2)

    def record_correction(self, intent_id: str, original_confidence: float) -> None:
        """Enforce Spec 66, 67: Evaluate intent predictions against user corrections."""
        self._corrections_count += 1
        logger.info("Recorded user correction on intent %s (original_conf=%.2f)", intent_id, original_confidence)

    def record_confirmation(self, intent_id: str) -> None:
        self._confirmations_count += 1

    @property
    def calibration_ratio(self) -> float:
        total = self._corrections_count + self._confirmations_count
        return (self._confirmations_count / total) if total > 0 else 1.0
