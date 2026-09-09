"""Contradiction detection, classification, and hierarchy-based resolution for Kairo Truth Engine (Task 42)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from pydantic import BaseModel, ConfigDict, Field

from app.verification.claims import Claim, ClaimType, TruthStatus


def utc_now() -> datetime:
    return datetime.now(UTC)


class ContradictionType(str, Enum):
    """Classifications of conflicting assertions (Spec 73)."""

    DIRECT_CONFLICT = "DIRECT_CONFLICT"        # Same subject/predicate, opposing objects at same time/version
    TEMPORAL_CONFLICT = "TEMPORAL_CONFLICT"    # Newer observation refutes older claim
    SCOPE_CONFLICT = "SCOPE_CONFLICT"          # Claim applied to wrong project or environment
    VERSION_CONFLICT = "VERSION_CONFLICT"      # Outdated version trying to overwrite newer state
    SOURCE_CONFLICT = "SOURCE_CONFLICT"        # Two external sources asserting incompatible facts
    STATE_CONFLICT = "STATE_CONFLICT"          # Derived state contradicts authoritative database record


class Contradiction(BaseModel):
    """An identified empirical contradiction between two claims or observations."""

    model_config = ConfigDict(extra="ignore")

    contradiction_id: str = Field(default_factory=lambda: f"ctd_{uuid.uuid4().hex[:10]}")
    contradiction_type: ContradictionType
    claim_a_id: str
    claim_b_id: str
    subject: str
    predicate: str
    object_a: str
    object_b: str
    detected_at: datetime = Field(default_factory=utc_now)
    resolved: bool = False
    winning_claim_id: str | None = None
    resolution_rationale: str | None = None

    @property
    def conflict_type(self) -> ContradictionType:
        return self.contradiction_type

    @property
    def target_claim_id(self) -> str:
        return self.claim_a_id

    @property
    def conflicting_claim_id(self) -> str:
        return self.claim_b_id

    def to_dict(self) -> dict[str, Any]:
        return {
            "contradiction_id": self.contradiction_id,
            "conflict_type": self.contradiction_type.value,
            "target_claim_id": self.claim_a_id,
            "conflicting_claim_id": self.claim_b_id,
            "subject": self.subject,
            "predicate": self.predicate,
            "object_a": self.object_a,
            "object_b": self.object_b,
            "detected_at": self.detected_at.isoformat(),
            "resolved": self.resolved,
            "winning_claim_id": self.winning_claim_id,
            "resolution_rationale": self.resolution_rationale,
        }


class ContradictionEngine:
    """Detects and resolves contradictions using evidence hierarchy rules (Spec 77)."""

    # Resolution authority hierarchy (higher index = higher authority)
    AUTHORITY_RANKS = {
        ClaimType.MODEL_ASSERTION: 1,
        ClaimType.INFERENCE: 2,
        ClaimType.HYPOTHESIS: 3,
        ClaimType.PLAN_EXPECTATION: 4,
        ClaimType.USER_ASSERTION: 5,
        ClaimType.TOOL_REPORT: 6,
        ClaimType.STATE: 7,
        ClaimType.FACT: 8,
    }

    def detect_conflicts(self, target_claim: Claim, other_claims: list[Claim]) -> list[Contradiction]:
        """Detect all conflicts between a target claim and a list of claims."""
        conflicts = []
        for other in other_claims:
            c = self.detect_contradiction(target_claim, other)
            if c:
                conflicts.append(c)
        return conflicts

    def resolve_conflict(self, claim_a: Claim, claim_b: Claim) -> Claim:
        """Resolve a conflict between two claims."""
        c = self.detect_contradiction(claim_a, claim_b)
        if not c:
            return claim_a
        return self.resolve_contradiction(c, claim_a, claim_b)

    @classmethod
    def detect_contradiction(cls, claim_a: Claim, claim_b: Claim) -> Contradiction | None:
        """Evaluate if two claims contradict each other."""
        sub_a = (claim_a.subject or "").strip().lower()
        sub_b = (claim_b.subject or "").strip().lower()
        pred_a = (claim_a.predicate or "").strip().lower()
        pred_b = (claim_b.predicate or "").strip().lower()

        # Must share same subject and predicate to directly conflict
        if not sub_a or not sub_b or sub_a != sub_b:
            return None
        if not pred_a or not pred_b or pred_a != pred_b:
            return None

        # Scope check (Spec 76): Different project scopes do not conflict
        proj_a = claim_a.scope.get("project_id") if isinstance(claim_a.scope, dict) else getattr(claim_a.scope, "project_id", None)
        proj_b = claim_b.scope.get("project_id") if isinstance(claim_b.scope, dict) else getattr(claim_b.scope, "project_id", None)
        if proj_a and proj_b and proj_a != proj_b:
            return None

        # If object representations match, there is no conflict
        obj_a = (claim_a.object_ref or "").strip().lower()
        obj_b = (claim_b.object_ref or "").strip().lower()
        if obj_a == obj_b:
            return None

        # Direct vs Temporal Conflict
        obs_a = claim_a.observed_at
        obs_b = claim_b.observed_at
        if obs_a.tzinfo is None:
            obs_a = obs_a.replace(tzinfo=UTC)
        if obs_b.tzinfo is None:
            obs_b = obs_b.replace(tzinfo=UTC)

        time_diff = abs((obs_a - obs_b).total_seconds())
        if time_diff > 60.0:
            c_type = ContradictionType.TEMPORAL_CONFLICT
        else:
            c_type = ContradictionType.DIRECT_CONFLICT

        return Contradiction(
            contradiction_type=c_type,
            claim_a_id=claim_a.claim_id,
            claim_b_id=claim_b.claim_id,
            subject=claim_a.subject or "",
            predicate=claim_a.predicate or "",
            object_a=claim_a.object_ref or "",
            object_b=claim_b.object_ref or "",
        )

    @classmethod
    def resolve_contradiction(cls, contradiction: Contradiction, claim_a: Claim, claim_b: Claim) -> Claim:
        """Resolve contradiction using authority hierarchy and timestamps (Spec 77)."""
        rank_a = cls.AUTHORITY_RANKS.get(claim_a.claim_type, 1)
        rank_b = cls.AUTHORITY_RANKS.get(claim_b.claim_type, 1)

        # 1. Authority Hierarchy
        if rank_a != rank_b:
            winner, loser = (claim_a, claim_b) if rank_a > rank_b else (claim_b, claim_a)
            contradiction.resolved = True
            contradiction.winning_claim_id = winner.claim_id
            contradiction.resolution_rationale = (
                f"Resolved by authority hierarchy: {winner.claim_type.value} supersedes {loser.claim_type.value}."
            )
            loser.truth_status = TruthStatus.CONTRADICTED
            return winner

        # 2. Temporal Hierarchy (newer observation wins for same authority tier)
        obs_a = claim_a.observed_at
        obs_b = claim_b.observed_at
        if obs_a.tzinfo is None:
            obs_a = obs_a.replace(tzinfo=UTC)
        if obs_b.tzinfo is None:
            obs_b = obs_b.replace(tzinfo=UTC)

        if obs_a != obs_b:
            winner, loser = (claim_a, claim_b) if obs_a > obs_b else (claim_b, claim_a)
            contradiction.resolved = True
            contradiction.winning_claim_id = winner.claim_id
            contradiction.resolution_rationale = (
                f"Resolved by temporal precedence: newer observation ({winner.observed_at.isoformat()}) supersedes older."
            )
            loser.truth_status = TruthStatus.CONTRADICTED
            return winner

        # Unresolved stalemate
        contradiction.resolved = False
        contradiction.resolution_rationale = "Unresolved contradiction between equal-authority assertions."
        claim_a.truth_status = TruthStatus.CONTRADICTED
        claim_b.truth_status = TruthStatus.CONTRADICTED
        return claim_a
