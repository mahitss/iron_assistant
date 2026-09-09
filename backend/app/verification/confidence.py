"""Confidence Calibration & Uncertainty Engine for Kairo (Task 42).

Provides structured confidence levels (LOW, MEDIUM, HIGH), multi-factor
confidence computation, uncertainty classifications, and historical calibration
metrics without producing fake pseudo-exact numbers.
"""

from __future__ import annotations

import enum
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.verification.claims import Claim, TruthStatus
from app.verification.evidence import Evidence

logger = logging.getLogger("kairo.verification.confidence")


class ConfidenceLevel(str, enum.Enum):
    """Structured confidence classifications (Spec 84)."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class UncertaintyState(str, enum.Enum):
    """Structured uncertainty representation (Spec 89)."""

    KNOWN = "KNOWN"
    LIKELY = "LIKELY"
    UNCERTAIN = "UNCERTAIN"
    UNKNOWN = "UNKNOWN"
    CONTRADICTORY = "CONTRADICTORY"


@dataclass
class ConfidenceReport:
    """Calibrated confidence assessment report."""

    level: ConfidenceLevel
    uncertainty_state: UncertaintyState
    score: float  # Normalized 0.0 to 1.0 internally
    factors: dict[str, float]  # Component weights: evidence_quality, freshness, independence, coverage, contradictions
    explanation: str
    calibrated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "level": self.level.value,
            "uncertainty_state": self.uncertainty_state.value,
            "score": round(self.score, 3),
            "factors": {k: round(v, 3) for k, v in self.factors.items()},
            "explanation": self.explanation,
            "calibrated_at": self.calibrated_at.isoformat(),
        }


class ConfidenceCalibrator:
    """Calibrates confidence based on empirical evidence factors and past outcomes."""

    def __init__(self) -> None:
        # Calibration bin tracking for historical scoring: (predicted_bin -> [correct_count, total_count])
        self._calibration_bins: dict[str, list[int]] = {
            "LOW": [0, 0],
            "MEDIUM": [0, 0],
            "HIGH": [0, 0],
        }

    def calibrate(
        self,
        claim: Claim,
        evidences: list[Evidence],
        has_contradictions: bool = False,
        verification_passed: bool | None = None,
    ) -> ConfidenceReport:
        """Calculate calibrated confidence score and level.
        
        Evaluates:
        1. Evidence quality & reliability (Spec 85)
        2. Freshness
        3. Source independence
        4. Verification coverage
        5. Contradiction penalty
        """
        if not evidences:
            return ConfidenceReport(
                level=ConfidenceLevel.LOW,
                uncertainty_state=UncertaintyState.UNKNOWN,
                score=0.1,
                factors={
                    "evidence_quality": 0.0,
                    "freshness": 0.0,
                    "independence": 0.0,
                    "coverage": 0.0,
                    "contradictions": 0.0,
                },
                explanation="No empirical evidence available to support confidence.",
            )

        # 1. Evidence Quality (avg reliability)
        qualities = [ev.calculate_reliability() for ev in evidences]
        avg_quality = sum(qualities) / len(qualities) if qualities else 0.0

        # 2. Freshness Factor
        now = datetime.now(timezone.utc)
        freshness_scores = []
        for ev in evidences:
            obs = ev.observed_at
            if obs.tzinfo is None:
                obs = obs.replace(tzinfo=timezone.utc)
            age = (now - obs).total_seconds()
            freshness_scores.append(max(0.0, min(1.0, 1.0 - (age / 3600.0))))
        avg_freshness = sum(freshness_scores) / len(freshness_scores) if freshness_scores else 0.0

        # 3. Source Independence
        unique_origins = {f"{ev.source_type.value}:{ev.source_reference}" for ev in evidences}
        independence_score = min(1.0, len(unique_origins) / 2.0)

        # 4. Verification Coverage
        coverage_score = 1.0 if verification_passed is True else (0.5 if verification_passed is None else 0.0)

        # 5. Contradiction Penalty
        contradiction_factor = 0.0 if not has_contradictions else 0.6

        # Composite weighted score
        raw_score = (
            (avg_quality * 0.35)
            + (avg_freshness * 0.20)
            + (independence_score * 0.25)
            + (coverage_score * 0.20)
            - contradiction_factor
        )
        score = max(0.0, min(1.0, raw_score))

        # Determine level & uncertainty state
        if has_contradictions:
            level = ConfidenceLevel.LOW
            uncertainty_state = UncertaintyState.CONTRADICTORY
            explanation = "Contradictory evidence detected; confidence downgraded to LOW."
        elif claim.truth_status == TruthStatus.VERIFIED or (verification_passed and score >= 0.75):
            level = ConfidenceLevel.HIGH
            uncertainty_state = UncertaintyState.KNOWN
            explanation = "Independently verified with high-reliability fresh evidence."
        elif score >= 0.50 or claim.truth_status == TruthStatus.SUPPORTED:
            level = ConfidenceLevel.MEDIUM
            uncertainty_state = UncertaintyState.LIKELY
            explanation = "Supported by available evidence, but lacking complete independent corroboration."
        elif claim.truth_status in [TruthStatus.UNVERIFIED, TruthStatus.UNKNOWN]:
            level = ConfidenceLevel.LOW
            uncertainty_state = UncertaintyState.UNKNOWN
            explanation = "Unverified or insufficient evidence available."
        else:
            level = ConfidenceLevel.LOW
            uncertainty_state = UncertaintyState.UNCERTAIN
            explanation = "Low confidence due to stale, weak, or partial evidence."

        return ConfidenceReport(
            level=level,
            uncertainty_state=uncertainty_state,
            score=score,
            factors={
                "evidence_quality": avg_quality,
                "freshness": avg_freshness,
                "independence": independence_score,
                "coverage": coverage_score,
                "contradictions": contradiction_factor,
            },
            explanation=explanation,
        )

    def record_outcome(self, level: ConfidenceLevel, was_correct: bool) -> None:
        """Record verified outcome to calibrate future confidence bins."""
        bin_entry = self._calibration_bins.setdefault(level.value, [0, 0])
        if was_correct:
            bin_entry[0] += 1
        bin_entry[1] += 1

    def get_calibration_stats(self) -> dict[str, Any]:
        """Return historical calibration accuracy per confidence tier."""
        stats = {}
        for tier, (correct, total) in self._calibration_bins.items():
            accuracy = (correct / total) if total > 0 else 0.0
            stats[tier] = {
                "correct": correct,
                "total": total,
                "accuracy": round(accuracy, 3),
            }
        return stats
