"""Confidence and Decay Engine for Kairo Strategy Engine (Task 106).

Calculates holistic multi-factor strategy confidence, manages temporal validity windows,
detects capability drift, and triggers revalidation requirements.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import logging
from typing import Any, Dict, List, Optional

from app.strategy.domain import Strategy, StrategyStatus, utc_now

logger = logging.getLogger("kairo.strategy.confidence_engine")


class StrategyHealthReport:
    """Detailed health, confidence, and freshness assessment."""

    def __init__(
        self,
        strategy_id: str,
        overall_confidence: float,
        uncertainty: float,
        is_stale: bool,
        is_drift_detected: bool,
        revalidation_required: bool,
        factors: Dict[str, float],
        recommendations: List[str],
    ) -> None:
        self.strategy_id = strategy_id
        self.overall_confidence = overall_confidence
        self.uncertainty = uncertainty
        self.is_stale = is_stale
        self.is_drift_detected = is_drift_detected
        self.revalidation_required = revalidation_required
        self.factors = factors
        self.recommendations = recommendations


class ConfidenceAndDecayEngine:
    """Computes multi-factor epistemic confidence and tracks temporal validity."""

    def __init__(
        self,
        stale_threshold_days: int = 14,
        drift_success_rate_drop: float = 0.20,
    ) -> None:
        self.stale_threshold_days = stale_threshold_days
        self.drift_success_rate_drop = drift_success_rate_drop

    def evaluate_health_and_confidence(
        self,
        strategy: Strategy,
        current_time: Optional[datetime] = None,
    ) -> StrategyHealthReport:
        """Compute multi-factor confidence and assess freshness and drift."""
        now = current_time or utc_now()
        factors: Dict[str, float] = {}
        recommendations: List[str] = []

        # 1. Evidence Quantity Factor (logarithmic saturation)
        ev_count = len(strategy.evidences)
        if ev_count == 0:
            quantity_factor = 0.2
        elif ev_count < 5:
            quantity_factor = 0.5
        elif ev_count < 15:
            quantity_factor = 0.8
        else:
            quantity_factor = 1.0
        factors["evidence_quantity"] = quantity_factor

        # 2. Counterexample / Exception Penalty
        ce_count = len(strategy.counterexamples)
        if ce_count == 0:
            ce_penalty = 0.0
        else:
            # Ratio of counterexamples to total evidence
            ratio = ce_count / max(1, ev_count + ce_count)
            ce_penalty = min(0.5, ratio * 1.5)
        factors["counterexample_penalty"] = ce_penalty

        # 3. Recency & Temporal Decay
        last_eval = strategy.last_validated_at or strategy.created_at
        age_days = (now - last_eval).total_seconds() / 86400.0
        max_days = strategy.validity_window_seconds / 86400.0

        if age_days > max_days:
            recency_factor = max(0.1, 1.0 - (age_days - max_days) * 0.05)
            is_stale = True
            recommendations.append(f"Strategy age ({age_days:.1f} days) exceeds validity window ({max_days:.1f} days). Marked STALE.")
        else:
            recency_factor = 1.0
            is_stale = False
        factors["recency"] = recency_factor

        # 4. Historical Empirical Success
        success_factor = strategy.success_rate if strategy.usage_count > 0 else 0.5
        factors["empirical_success"] = success_factor

        # 5. Drift Detection
        is_drift_detected = False
        if strategy.usage_count >= 10:
            # If recent performance deviates significantly from initial validated confidence
            if (strategy.confidence - strategy.success_rate) >= self.drift_success_rate_drop:
                is_drift_detected = True
                recommendations.append(
                    f"Drift detected: Recent success rate ({strategy.success_rate:.2f}) dropped > {self.drift_success_rate_drop:.2f} below nominal confidence ({strategy.confidence:.2f})."
                )

        # Multi-factor aggregate confidence calculation
        raw_conf = (
            0.30 * quantity_factor +
            0.35 * success_factor +
            0.35 * recency_factor
        ) - ce_penalty

        overall_confidence = max(0.05, min(0.98, raw_conf))
        uncertainty = 1.0 - overall_confidence

        revalidation_required = is_stale or is_drift_detected or (ce_count > 3)

        # Update strategy model in place
        strategy.confidence = round(overall_confidence, 4)
        strategy.uncertainty = round(uncertainty, 4)
        strategy.is_stale = is_stale
        if is_stale and strategy.lifecycle_status == StrategyStatus.AVAILABLE:
            strategy.lifecycle_status = StrategyStatus.EXPIRED

        return StrategyHealthReport(
            strategy_id=strategy.id,
            overall_confidence=strategy.confidence,
            uncertainty=strategy.uncertainty,
            is_stale=is_stale,
            is_drift_detected=is_drift_detected,
            revalidation_required=revalidation_required,
            factors=factors,
            recommendations=recommendations,
        )
