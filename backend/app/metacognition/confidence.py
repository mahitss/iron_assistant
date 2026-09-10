"""Confidence scoring, grounding, and calibration influences (INVARIANTS 26, 30, 31)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class ConfidenceEngine:
    """Computes grounded confidence scores based on empirical evidence, verification, and calibration adjustments."""

    def __init__(self, calibration_factor: float = 1.0) -> None:
        self.calibration_factor = calibration_factor  # Adjusted by ConfidenceCalibrator

    def calculate_confidence(
        self,
        source_tier: str,
        is_verified: bool,
        evidence_count: int = 1,
        has_contradictions: bool = False,
        is_inferred: bool = False,
    ) -> float:
        """INVARIANT 26: Confidence must never be arbitrary."""
        base = 0.5

        if source_tier in ("USER_EXPLICIT", "direct_user"):
            base = 0.95
        elif source_tier in ("SYSTEM_AUTHORITATIVE", "git_provider"):
            base = 0.90
        elif source_tier in ("VERIFIED_TOOL", "test_runner"):
            base = 0.85
        elif source_tier in ("OBSERVATION", "sensor"):
            base = 0.80
        elif source_tier in ("WEB_EXTERNAL", "unverified_document"):
            base = 0.50

        # Adjustments
        if is_verified:
            base = min(base + 0.15, 1.0)
        if is_inferred:
            base = min(base, 0.65)
        if has_contradictions:
            base = max(base - 0.40, 0.20)

        # Evidence count boost (logarithmic-like, up to +0.10)
        boost = min((evidence_count - 1) * 0.03, 0.10)
        base = min(base + boost, 1.0)

        # Apply empirical calibration factor
        final_conf = min(max(base * self.calibration_factor, 0.05), 1.0)
        return round(final_conf, 3)

    def set_calibration_factor(self, factor: float) -> None:
        """INVARIANT 30: Calibration influences future confidence."""
        self.calibration_factor = min(max(factor, 0.5), 1.5)
