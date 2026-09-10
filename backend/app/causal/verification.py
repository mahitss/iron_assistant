"""Causal verification system enforcing independent evidence thresholds and intervention testing (Task 55)."""

from __future__ import annotations

from typing import Any

from app.causal.schemas import (
    CausalHypothesis,
    EvidenceType,
    HypothesisStatus,
    VerificationStatus,
)


class VerificationThresholds:
    """Configurable requirements for elevating a hypothesis to verified causal relation."""

    def __init__(
        self,
        min_independent_sources: int = 2,
        require_intervention: bool = False,
        min_evidence_score: float = 2.0,
    ) -> None:
        self.min_independent_sources = min_independent_sources
        self.require_intervention = require_intervention
        self.min_evidence_score = min_evidence_score


class CausalVerificationEngine:
    """Verifies causal hypotheses against multi-source evidence and intervention outcomes.

    Prompt #82, #83: High confidence does not equal verification.
    Prompt #84, #85: Verified status requires meeting explicit evidence and intervention thresholds.
    """

    @staticmethod
    def verify_hypothesis(
        hypothesis: CausalHypothesis,
        intervention_evidence: dict[str, Any] | None = None,
        thresholds: VerificationThresholds | None = None,
    ) -> tuple[VerificationStatus, str, list[str]]:
        """Prompt #80, #81, #84, #86: Evaluate hypothesis verification status."""
        thresh = thresholds or VerificationThresholds()
        findings: list[str] = []

        if not hypothesis.evidence:
            return VerificationStatus.UNTESTED, "No empirical evidence attached to hypothesis.", findings

        # Track distinct evidence types and sources
        unique_sources = {ev.source for ev in hypothesis.evidence}
        evidence_types = {ev.type for ev in hypothesis.evidence}

        has_intervention = (
            EvidenceType.INTERVENTION in evidence_types
            or EvidenceType.EXPERIMENT in evidence_types
            or (intervention_evidence is not None and intervention_evidence.get("effect_matched"))
        )
        has_critical_or_strong = any(ev.strength.value in ("STRONG", "CRITICAL") for ev in hypothesis.evidence)

        # Check for contradictions
        if hypothesis.status == HypothesisStatus.CONTRADICTED:
            return VerificationStatus.REJECTED, "Hypothesis rejected due to contradictory empirical evidence.", findings

        # Verification logic
        if len(unique_sources) < thresh.min_independent_sources and not has_intervention:
            findings.append(f"Only {len(unique_sources)} independent source(s) available; requires {thresh.min_independent_sources}.")
            return (
                VerificationStatus.PARTIALLY_TESTED,
                "Hypothesis has initial evidence but lacks required independent source diversity.",
                findings,
            )

        # Check if intervention is required or passed
        if thresh.require_intervention and not has_intervention:
            findings.append("Configured threshold requires intervention testing before declaring verification.")
            return (
                VerificationStatus.SUPPORTED,
                "Hypothesis is strongly supported by observations but awaits intervention verification.",
                findings,
            )

        # If has critical/strong multi-source evidence or confirmed intervention
        if (has_intervention and has_critical_or_strong) or (len(unique_sources) >= 2 and has_critical_or_strong):
            findings.append(f"Verified via {len(unique_sources)} independent sources and strong/intervention evidence.")
            hypothesis.status = HypothesisStatus.VERIFIED
            return (
                VerificationStatus.VERIFIED,
                "Hypothesis meets all empirical criteria and is verified as a causal relation.",
                findings,
            )

        # Otherwise supported
        findings.append("Evidence supports hypothesis but does not reach the critical threshold for complete verification.")
        hypothesis.status = HypothesisStatus.SUPPORTED
        return (
            VerificationStatus.SUPPORTED,
            "Hypothesis is supported by current evidence.",
            findings,
        )
