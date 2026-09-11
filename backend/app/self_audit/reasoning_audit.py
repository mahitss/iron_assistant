"""Reasoning Quality Audit, Claim Evaluation, and Decision Outcome Comparison (Task 67)."""

from __future__ import annotations

import logging
from typing import Any

from app.self_audit.schemas import (
    ErrorCategory,
    ErrorSeverity,
)

logger = logging.getLogger("kairo.self_audit.reasoning_audit")


class ReasoningAuditor:
    """Audits structured reasoning traces for epistemic fallacies, false certainty, and bias (Spec 10, 11).

    Invariant: Preserves structured metadata only; does NOT expose private chain-of-thought.
    """

    @classmethod
    def audit_reasoning_trace(
        cls,
        claims: list[str],
        assumptions: list[str],
        evidence_references: list[str],
        confidence_reported: float,
        contradictory_evidence: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Evaluate a structured reasoning process against epistemic audit checks."""
        findings: list[dict[str, Any]] = []
        contra = contradictory_evidence or []

        # 1. False Certainty Check (Spec 10)
        if confidence_reported >= 0.99 and len(evidence_references) < 3:
            findings.append(
                {
                    "check": "FALSE_CERTAINTY",
                    "category": ErrorCategory.CALIBRATION_ERROR.value,
                    "severity": ErrorSeverity.HIGH.value,
                    "description": f"Reported certainty ({confidence_reported:.2f}) is unjustified given limited evidence ({len(evidence_references)} citations).",
                    "confidence": 0.85,
                }
            )

        # 2. Unsupported Assumptions (Spec 10)
        for asm in assumptions:
            if not any(asm.lower() in ev.lower() for ev in evidence_references):
                findings.append(
                    {
                        "check": "UNSUPPORTED_ASSUMPTION",
                        "category": ErrorCategory.REASONING_ERROR.value,
                        "severity": ErrorSeverity.MEDIUM.value,
                        "description": f"Critical assumption '{asm}' has no corroborating evidence citations.",
                        "confidence": 0.8,
                    }
                )

        # 3. Confirmation Bias (Spec 10)
        if contra and len(evidence_references) > 0:
            ignored_contra = [
                c for c in contra if not any(c.lower() in ev.lower() for ev in evidence_references)
            ]
            if ignored_contra:
                findings.append(
                    {
                        "check": "CONFIRMATION_BIAS",
                        "category": ErrorCategory.REASONING_ERROR.value,
                        "severity": ErrorSeverity.HIGH.value,
                        "description": f"Reasoning ignored {len(ignored_contra)} contradictory evidence points while selecting supportive evidence.",
                        "confidence": 0.9,
                    }
                )

        # 4. Causal Overreach (Spec 10)
        for claim in claims:
            low = claim.lower()
            if (
                any(k in low for k in ["causes", "proves", "guarantees", "directly caused"])
                and "correlat" in low
            ):
                findings.append(
                    {
                        "check": "CAUSAL_OVERREACH",
                        "category": ErrorCategory.REASONING_ERROR.value,
                        "severity": ErrorSeverity.MEDIUM.value,
                        "description": f"Claim '{claim}' appears to confuse correlation with definitive causation.",
                        "confidence": 0.75,
                    }
                )

        # 5. Premature Convergence (Spec 10)
        if len(claims) == 1 and len(assumptions) > 2 and confidence_reported > 0.85:
            findings.append(
                {
                    "check": "PREMATURE_CONVERGENCE",
                    "category": ErrorCategory.PLANNING_ERROR.value,
                    "severity": ErrorSeverity.LOW.value,
                    "description": "Reasoning converged on a single conclusion without evaluating competing alternatives despite multiple critical assumptions.",
                    "confidence": 0.7,
                }
            )

        return findings


class ClaimAuditor:
    """Audits important claims against currency, independence, and verification (Spec 12)."""

    @classmethod
    def audit_claim(
        cls,
        claim: str,
        sources: list[str],
        is_verified: bool = False,
        contradictory_sources: list[str] | None = None,
    ) -> dict[str, Any]:
        """Verify claim pedigree and detect contradictory evidence."""
        contra = contradictory_sources or []
        is_independent = len(set(sources)) >= 2

        evaluation = {
            "claim": claim,
            "source_count": len(sources),
            "is_independently_supported": is_independent,
            "is_empirically_verified": is_verified,
            "has_contradictions": len(contra) > 0,
            "contradiction_count": len(contra),
            "quality_grade": "VERIFIED"
            if (is_verified and is_independent and not contra)
            else "UNVERIFIED_OR_DISPUTED",
        }

        if contra and not is_verified:
            logger.warning("CLAIM_DISPUTED: '%s' has %d contradictory sources.", claim, len(contra))

        return evaluation


class DecisionAuditor:
    """Evaluates decisions by comparing predicted vs actual outcomes (Spec 13, 14)."""

    @classmethod
    def audit_decision(
        cls,
        decision_id: str,
        objective: str,
        selected_option: str,
        predicted_outcome: str,
        actual_outcome: str | None = None,
        constraints_violated: list[str] | None = None,
    ) -> dict[str, Any]:
        """Classify decision accuracy and detect decision errors."""
        violations = constraints_violated or []
        outcome_matched = False
        error_class: str | None = None

        if actual_outcome:
            # Check if expected key keywords match actual outcome
            pred_words = set(predicted_outcome.lower().split())
            act_words = set(actual_outcome.lower().split())
            overlap = len(pred_words.intersection(act_words))
            outcome_matched = overlap >= max(1, len(pred_words) // 3)

            if not outcome_matched:
                error_class = "PREDICTION_DISCREPANCY"
            if violations:
                error_class = "CONSTRAINT_VIOLATION"

        return {
            "decision_id": decision_id,
            "objective": objective,
            "selected_option": selected_option,
            "predicted_outcome": predicted_outcome,
            "actual_outcome": actual_outcome,
            "outcome_matched": outcome_matched,
            "has_error": error_class is not None,
            "decision_error_class": error_class,
            "constraints_violated": violations,
        }
