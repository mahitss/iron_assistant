"""Self-Correction & Oscillation Protection Engine for Kairo (Task 42).

Enforces:
1. Canonical loop: CLAIM -> VERIFY -> FAIL -> DIAGNOSE -> CORRECT -> REVERIFY (Spec 135).
2. Oscillation detection: A -> B -> A -> B stops and escalates (Spec 137).
3. Bounded automatic corrections (Spec 136).
4. Transparent user-facing admission (Spec 82, 144).
5. Safety boundaries: cannot alter security, policy, permissions, authorization, audit (Spec 141).
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.verification.claims import Claim, ClaimType, TruthStatus
from app.verification.evidence import Evidence

logger = logging.getLogger("kairo.verification.self_correction")


@dataclass
class Correction:
    """Record of a self-correction event (Spec 79)."""

    correction_id: str
    original_claim_id: str
    original_statement: str
    corrected_statement: str
    evidence_ids: list[str]
    reason: str
    user_admission: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = "APPLIED"  # "APPLIED", "ESCALATED", "BLOCKED_BY_BOUNDARY"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "correction_id": self.correction_id,
            "original_claim_id": self.original_claim_id,
            "original_statement": self.original_statement,
            "corrected_statement": self.corrected_statement,
            "evidence_ids": self.evidence_ids,
            "reason": self.reason,
            "user_admission": self.user_admission,
            "timestamp": self.timestamp.isoformat(),
            "status": self.status,
            "metadata": self.metadata,
        }


class SelfCorrectionEngine:
    """Manages iterative self-correction, loop bounds, and oscillation detection."""

    def __init__(self, max_corrections_per_target: int = 3) -> None:
        self.max_corrections = max_corrections_per_target
        # History of transitions per target subject: subject -> [sequence of statements/values]
        self._target_history: dict[str, list[str]] = {}
        # Count of corrections applied per subject
        self._correction_counts: dict[str, int] = {}
        # Completed corrections log
        self._corrections_log: list[Correction] = []

    def detect_oscillation(self, subject: str, new_value: str) -> bool:
        """Detect oscillation patterns such as A -> B -> A -> B (Spec 137)."""
        history = self._target_history.get(subject, [])
        if len(history) < 3:
            return False

        normalized_new = new_value.strip().lower()
        last = history[-1].strip().lower()
        prev = history[-2].strip().lower()
        prev2 = history[-3].strip().lower() if len(history) >= 3 else ""

        # Check for immediate repeat flip: A -> B -> A -> (attempting B again)
        if normalized_new == prev and last == prev2 and normalized_new != last:
            logger.warning(
                "Oscillation detected for subject '%s': '%s' <-> '%s'",
                subject,
                normalized_new,
                last,
            )
            return True

        return False

    def can_correct(self, subject: str) -> tuple[bool, str]:
        """Check whether automatic correction attempt limit has been reached."""
        count = self._correction_counts.get(subject, 0)
        if count >= self.max_corrections * 2:
            return False, f"Maximum correction attempts ({self.max_corrections}) exceeded for '{subject}'"
        return True, "OK"

    def format_user_admission(self, original_statement: str, verified_truth: str) -> str:
        """Format honest, concise user-facing admission (Spec 82, 144)."""
        return f"I was wrong about {original_statement.rstrip('.')}. Verification shows {verified_truth.rstrip('.')}."

    def attempt_correction(
        self,
        original_claim: Claim,
        corrected_statement: str,
        supporting_evidence: list[Evidence],
        reason: str,
    ) -> Correction:
        """Execute a structured self-correction with boundary and loop safety."""
        subject = original_claim.subject or original_claim.statement
        correction_id = f"corr-{uuid.uuid4().hex[:8]}"

        # Safety boundary check (Spec 141):
        sensitive_domains = {"security", "policy", "permissions", "authorization", "audit"}
        claim_domain = str(original_claim.scope.get("domain", "") if isinstance(original_claim.scope, dict) else "").lower()
        if claim_domain in sensitive_domains:
            logger.error(
                "Self-correction boundary violation blocked for sensitive domain '%s'",
                claim_domain,
            )
            corr = Correction(
                correction_id=correction_id,
                original_claim_id=original_claim.claim_id,
                original_statement=original_claim.statement,
                corrected_statement=corrected_statement,
                evidence_ids=[ev.evidence_id for ev in supporting_evidence],
                reason=f"Blocked: Self-correction cannot alter {claim_domain} policy or controls.",
                user_admission="Self-correction halted: Security and policy constraints require operator review.",
                status="BLOCKED_BY_BOUNDARY",
            )
            self._corrections_log.append(corr)
            return corr

        # Oscillation check
        if self.detect_oscillation(subject, corrected_statement):
            corr = Correction(
                correction_id=correction_id,
                original_claim_id=original_claim.claim_id,
                original_statement=original_claim.statement,
                corrected_statement=corrected_statement,
                evidence_ids=[ev.evidence_id for ev in supporting_evidence],
                reason="Oscillation detected between contradictory states. Escalating to UNRESOLVED_CONFLICT.",
                user_admission="I encountered conflicting evidence and cannot verify the true state without operator review.",
                status="ESCALATED",
                metadata={"unresolved_conflict": True},
            )
            self._corrections_log.append(corr)
            return corr

        # Loop bound check
        allowed, msg = self.can_correct(subject)
        if not allowed:
            corr = Correction(
                correction_id=correction_id,
                original_claim_id=original_claim.claim_id,
                original_statement=original_claim.statement,
                corrected_statement=corrected_statement,
                evidence_ids=[ev.evidence_id for ev in supporting_evidence],
                reason=msg,
                user_admission="I reached the maximum self-correction limit for this operation.",
                status="ESCALATED",
                metadata={"max_limit_reached": True},
            )
            self._corrections_log.append(corr)
            return corr

        # Track history & counts
        history = self._target_history.setdefault(subject, [])
        if not history:
            history.append(original_claim.statement)
        history.append(corrected_statement)
        self._correction_counts[subject] = self._correction_counts.get(subject, 0) + 1

        # Generate admission
        user_admission = self.format_user_admission(original_claim.statement, corrected_statement)

        corr = Correction(
            correction_id=correction_id,
            original_claim_id=original_claim.claim_id,
            original_statement=original_claim.statement,
            corrected_statement=corrected_statement,
            evidence_ids=[ev.evidence_id for ev in supporting_evidence],
            reason=reason,
            user_admission=user_admission,
            status="APPLIED",
        )
        self._corrections_log.append(corr)
        return corr

    def get_corrections_for_claim(self, claim_id: str) -> list[Correction]:
        """Retrieve historical corrections for a specific claim (Spec 143)."""
        return [c for c in self._corrections_log if c.original_claim_id == claim_id]

    def get_all_corrections(self) -> list[Correction]:
        """Return all logged corrections."""
        return list(self._corrections_log)
