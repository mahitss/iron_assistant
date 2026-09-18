"""Freshness, Caching & Dependency Invalidation Engine for Task 116.
Governs temporal validity, safe verification caching, revalidation triggers,
and dependency invalidation propagation across claim hierarchies.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple
import uuid

from app.claim_verification.domain import (
    Claim,
    EvidenceArtifact,
    SourceSnapshot,
    VerificationCase,
    VerificationCaseStatus,
    VerificationGap,
    VerificationResult,
)


class StalenessAndCacheEngine:
    """Manages cache validation, staleness evaluation, and dependency propagation."""

    DEFAULT_TTL_SECONDS = 3600  # 1 hour default

    @classmethod
    def is_verification_stale(
        cls,
        result: VerificationResult,
        max_age_seconds: Optional[float] = None,
        as_of: Optional[datetime] = None,
    ) -> Tuple[bool, str]:
        """Check whether a verification result has expired or exceeded max age."""
        now = as_of or datetime.now(timezone.utc)

        # Check explicit expiration date
        if result.expires_at and now > result.expires_at:
            return True, f"Verification expired at {result.expires_at.isoformat()}"

        # Check TTL
        ttl = max_age_seconds or cls.DEFAULT_TTL_SECONDS
        age = (now - result.verified_at).total_seconds()
        if age > ttl:
            return True, f"Verification age ({age:.0f}s) exceeds TTL ({ttl:.0f}s)"

        return False, "Verification remains fresh"

    @classmethod
    def can_reuse_cached_result(
        cls,
        cached_result: VerificationResult,
        target_claim: Claim,
        target_scope: Dict[str, Any],
        current_snapshots: List[SourceSnapshot],
    ) -> Tuple[bool, str]:
        """Strict conditions for reusing cached verification:
        Never serve stale verification as current!
        """
        # 1. Claim ID & text match
        if cached_result.claim_id != target_claim.claim_id:
            return False, "Claim ID mismatch"

        # 2. Check staleness
        is_stale, reason = cls.is_verification_stale(cached_result)
        if is_stale:
            return False, f"Stale: {reason}"

        # 3. Check scope compatibility
        for k, v in target_scope.items():
            if cached_result.scope.get(k) != v:
                return False, f"Scope mismatch for key '{k}'"

        # 4. Check whether any underlying source snapshot has expired
        now = datetime.now(timezone.utc)
        for snap in current_snapshots:
            if snap.expired_at and now > snap.expired_at:
                return False, f"Underlying source snapshot {snap.snapshot_id} has expired"

        return True, "Cached verification is valid and fresh"

    @classmethod
    def propagate_invalidation(
        cls,
        invalidated_claim_id: str,
        all_claims_by_id: Dict[str, Claim],
        active_cases_by_claim_id: Dict[str, VerificationCase],
    ) -> List[Tuple[str, str]]:
        """Propagate invalidation to dependent claims.
        Returns list of (case_id, reason) that require revalidation.
        """
        requires_revalidation: List[Tuple[str, str]] = []
        visited: Set[str] = set()
        queue = [invalidated_claim_id]

        while queue:
            curr_id = queue.pop(0)
            if curr_id in visited:
                continue
            visited.add(curr_id)

            # Check every claim to see if it depends on curr_id
            for cid, claim in all_claims_by_id.items():
                if curr_id in claim.dependencies or any(curr_id in f.dependencies for f in claim.fragments):
                    # Invalidate child claim
                    if cid in active_cases_by_claim_id:
                        case = active_cases_by_claim_id[cid]
                        case.status = VerificationCaseStatus.REVALIDATION_REQUIRED
                        requires_revalidation.append(
                            (case.case_id, f"Dependency claim {curr_id} was invalidated or updated")
                        )
                    queue.append(cid)

        return requires_revalidation

    @classmethod
    def identify_verification_gaps(
        cls,
        case_id: str,
        claim: Claim,
        artifacts: List[EvidenceArtifact],
    ) -> List[VerificationGap]:
        """Identify missing evidence requirements or unresolved assumptions as VerificationGaps."""
        gaps: List[VerificationGap] = []

        # 1. Missing evidence for expected evidence types
        present_types = set()
        for art in artifacts:
            present_types.add(art.quality_profile.directness)

        for req in claim.expected_evidence_types:
            if req not in present_types and len(artifacts) < 2:
                gaps.append(
                    VerificationGap(
                        gap_id=f"gap_{uuid.uuid4().hex[:10]}",
                        case_id=case_id,
                        missing_evidence_desc=f"Missing independent {req} evidence for '{claim.subject} {claim.predicate}'",
                        impact_reason=f"Without {req} evidence, corroboration remains partial and uncertainty is high",
                        affected_claim_id=claim.claim_id,
                        possible_methods=["ACTIVE_OBSERVATION", "TELEMETRY_CORRELATION", "LOG_CORRELATION"],
                        expected_info_gain=0.75,
                        cost=0.1,
                        risk=0.05,
                        urgency=0.6,
                        created_at=datetime.now(timezone.utc),
                    )
                )

        # 2. Check for fragments with zero evidence
        for frag in claim.fragments:
            frag_words = set(frag.statement.lower().split())
            covered = False
            for art in artifacts:
                art_words = set(art.content_text.lower().split())
                if frag_words and art_words and len(frag_words.intersection(art_words)) / len(frag_words) > 0.3:
                    covered = True
                    break
            if not covered:
                gaps.append(
                    VerificationGap(
                        gap_id=f"gap_{uuid.uuid4().hex[:10]}",
                        case_id=case_id,
                        missing_evidence_desc=f"Sub-claim fragment has zero supporting evidence: '{frag.statement}'",
                        impact_reason="Sub-claim remains completely unverified, blocking full claim verification",
                        affected_claim_id=claim.claim_id,
                        possible_methods=["SOURCE_RETRIEVAL", "DATABASE_REQUERY"],
                        expected_info_gain=0.85,
                        cost=0.15,
                        risk=0.05,
                        urgency=0.7,
                        created_at=datetime.now(timezone.utc),
                    )
                )

        return gaps
