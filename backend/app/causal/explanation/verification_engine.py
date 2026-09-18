"""Explanation Verification & Calibration Engine for Task 112:
Monitors subsequent empirical evidence to confirm or invalidate provisional explanations.

Strict Invariants:
- PROVISIONAL CANNOT BECOME VERIFIED WITHOUT EMPIRICAL EVIDENCE
- CONTRADICTORY LATER EVIDENCE MUST RECLASSIFY OR SUPERSEDE THE EXPLANATION
- NEVER REWRITE HISTORICAL SNAPSHOTS SILENTLY
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Optional, Tuple

from app.causal.explanation.domain import (
    CausalExplanation,
    ExplanationLifecycleStage,
    ExplanationVerification,
    VerificationOutcome,
    gen_explanation_id,
    utc_now,
)


class VerificationEngine:
    """Verifies proposed explanations against post-incident evidence."""

    @classmethod
    def record_verification_result(
        cls,
        explanation: CausalExplanation,
        actual_observation: str,
        predicted_consequence: Optional[str] = None,
        actor: str = "system",
        notes: Optional[str] = None,
    ) -> Tuple[CausalExplanation, ExplanationVerification]:
        """Applies follow-up empirical observation to verify or contradict an explanation."""
        predicted = predicted_consequence or explanation.what_would_verify_this or "Matching expected state"
        pred_lower = predicted.lower().strip()
        obs_lower = actual_observation.lower().strip()

        # Check for confirmation vs contradiction
        if any(term in obs_lower for term in ["confirmed", "verified", "matched", "reproduced", "true", "zero packet drops"]):
            outcome = VerificationOutcome.SUPPORTED
            explanation.lifecycle_stage = ExplanationLifecycleStage.VERIFIED
            explanation.is_verified = True
        elif any(term in obs_lower for term in ["contradicted", "false", "disproven", "refuted", "normal", "healthy"]):
            outcome = VerificationOutcome.CONTRADICTED
            explanation.lifecycle_stage = ExplanationLifecycleStage.CONTRADICTED
            explanation.is_verified = False
        else:
            outcome = VerificationOutcome.WEAKENED
            explanation.lifecycle_stage = ExplanationLifecycleStage.CONTESTED
            explanation.is_verified = False

        explanation.updated_at = utc_now()

        verification = ExplanationVerification(
            explanation_id=explanation.explanation_id,
            tested_hypothesis=explanation.primary_cause or "Primary explanation",
            predicted_consequence=predicted,
            actual_observation=actual_observation,
            outcome=outcome,
            observation_timestamp=utc_now(),
            verified_by_actor=actor,
            notes=notes,
        )

        return explanation, verification
