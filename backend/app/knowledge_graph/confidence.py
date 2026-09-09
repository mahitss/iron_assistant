"""Confidence scoring, calibration, and anti-truth-conflation guards (INVARIANTS 8, 9, 231)."""

from __future__ import annotations

from typing import Any, Dict
from app.knowledge_graph.schemas import ConfidenceTier, ProvenanceType


class ConfidenceCalculator:
    """Calculates and calibrates confidence scores based on provenance tier.

    INVARIANT 9: Confidence != Truth. Confidence is an operational probability, not definitive proof.
    """

    DEFAULT_WEIGHTS = {
        ConfidenceTier.EXPLICIT: 1.0,
        ConfidenceTier.VERIFIED: 0.95,
        ConfidenceTier.OBSERVED: 0.80,
        ConfidenceTier.INFERRED: 0.50,
    }

    @classmethod
    def calculate_confidence(
        cls,
        tier: ConfidenceTier,
        provenance_type: ProvenanceType,
        repeated_confirmations: int = 0,
    ) -> float:
        base = cls.DEFAULT_WEIGHTS.get(tier, 0.5)

        # Learning & repetition bonus (bounded, asymptotic)
        bonus = min(repeated_confirmations * 0.05, 0.15) if tier != ConfidenceTier.INFERRED else 0.0
        score = min(base + bonus, 1.0)
        return round(score, 2)
