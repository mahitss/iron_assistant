"""Contradiction reconciliation, domain authority resolution, and evidence arbitration (INVARIANTS 95-99)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Dict, List, Optional
from app.knowledge_graph.schemas import (
    AssertionSchema,
    AssertionStatus,
    ContradictionSchema,
)


class ContradictionReconciler:
    """Arbitrates conflicting assertions based on domain authority rules."""

    @staticmethod
    def reconcile(
        contradiction: ContradictionSchema,
        assertions_map: Dict[str, AssertionSchema],
        prefer_user_override: bool = True,
    ) -> Dict[str, Any]:
        """Resolves conflict between assertions.

        Authority rules:
        1. Explicit current user statements override older inferred assertions (INVARIANT 98).
        2. Verified sources override unverified inferences (INVARIANT 95).
        3. Authoritative system domains (e.g. GitHub for repos) override memory (INVARIANT 96 & 97).
        4. More recent timestamp breaks ties.
        """
        candidates = []
        for c in contradiction.conflicting_assertions:
            aid = c["assertion_id"]
            if aid in assertions_map:
                candidates.append(assertions_map[aid])

        if not candidates:
            return {"status": "UNRESOLVED", "reason": "No active assertion instances found."}

        def score_candidate(a: AssertionSchema) -> float:
            score = a.confidence * 10.0
            src_type = a.source.get("source_type") or a.source.get("source", "")
            if src_type in ("USER", "direct_user_statement", "explicit_user"):
                score += 50.0  # INVARIANT 98: User statement authority
            if src_type in ("GITHUB", "git_provider", "system_authoritative"):
                score += 40.0  # INVARIANT 97: Authoritative provider
            if not a.is_inferred:
                score += 20.0
            # Recency bonus (up to 1.0)
            score += a.timestamp.timestamp() / 1e10
            return score

        sorted_candidates = sorted(candidates, key=score_candidate, reverse=True)
        winner = sorted_candidates[0]
        losers = sorted_candidates[1:]

        # Mark winner active, losers superseded/contradicted
        winner.status = AssertionStatus.ACTIVE
        for loser in losers:
            loser.status = AssertionStatus.SUPERSEDED

        resolution = {
            "resolved_at": datetime.now(UTC).isoformat(),
            "winning_assertion_id": winner.assertion_id,
            "winning_value": winner.object,
            "superseded_assertions": [l.assertion_id for l in losers],
            "authority_reason": f"Selected assertion {winner.assertion_id[:8]} with highest authority and recency.",
        }

        contradiction.resolution = resolution
        contradiction.status = "RESOLVED"

        return resolution
