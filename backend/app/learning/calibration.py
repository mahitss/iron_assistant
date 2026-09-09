"""Confidence calibration and sample reliability for Kairo Learning Engine (Task 43)."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any


@dataclass
class CalibratedConfidence:
    """Confidence interval and tier accounting for sample size (Spec 38, 186, 187)."""

    tier: str  # LOW, MEDIUM, HIGH
    sample_size: int
    point_estimate: float  # e.g. success rate
    margin_of_error: float
    lower_bound: float
    upper_bound: float
    has_statistical_significance: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "tier": self.tier,
            "sample_size": self.sample_size,
            "point_estimate": round(self.point_estimate, 3),
            "margin_of_error": round(self.margin_of_error, 3),
            "lower_bound": round(self.lower_bound, 3),
            "upper_bound": round(self.upper_bound, 3),
            "has_statistical_significance": self.has_statistical_significance,
        }


class ConfidenceCalibrator:
    """Computes confidence intervals and rejects false precision from tiny samples."""

    @staticmethod
    def calibrate(sample_size: int, successes: int) -> CalibratedConfidence:
        if sample_size == 0:
            return CalibratedConfidence(
                tier="LOW",
                sample_size=0,
                point_estimate=0.0,
                margin_of_error=1.0,
                lower_bound=0.0,
                upper_bound=1.0,
                has_statistical_significance=False,
            )

        p = successes / sample_size

        # Wilson score interval approximation for small sample proportion
        z = 1.96  # 95% confidence
        denominator = 1 + (z**2 / sample_size)
        centre_adjusted_probability = (p + (z**2 / (2 * sample_size))) / denominator
        margin = (z * math.sqrt((p * (1 - p) / sample_size) + (z**2 / (4 * sample_size**2)))) / denominator

        lower = max(0.0, centre_adjusted_probability - margin)
        upper = min(1.0, centre_adjusted_probability + margin)

        if sample_size >= 30 and lower >= 0.80:
            tier = "HIGH"
        elif sample_size >= 10:
            tier = "MEDIUM"
        else:
            tier = "LOW"

        return CalibratedConfidence(
            tier=tier,
            sample_size=sample_size,
            point_estimate=p,
            margin_of_error=margin,
            lower_bound=lower,
            upper_bound=upper,
            has_statistical_significance=sample_size >= 15,
        )
