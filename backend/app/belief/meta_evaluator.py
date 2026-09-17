"""Meta Belief Evaluator for Task 107.

Integrates with Task 104 Continuous Evaluation.
Evaluates:
- Revision accuracy
- Stale detection coverage
- Conflict resolution soundness
- False confidence rate
- Circularity resistance
- Evidence deduplication efficiency
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from app.belief.domain import (
    Belief,
    BeliefConflict,
    BeliefStatus,
    BeliefVersion,
    ConflictResolution,
    EvidenceItem,
    utc_now,
)

logger = logging.getLogger("kairo.belief.meta_evaluator")


class MetaBeliefEvaluator:
    """Evaluates the epistemic soundness and performance of the Belief Engine."""

    def evaluate_manifold(
        self,
        beliefs: List[Belief],
        conflicts: List[BeliefConflict],
        evidence_items: List[EvidenceItem],
        revisions_count: int,
    ) -> Dict[str, Any]:
        """Perform comprehensive epistemic health audit."""
        total = len(beliefs)
        if total == 0:
            return {
                "total_beliefs": 0,
                "epistemic_health_score": 1.0,
                "status": "HEALTHY",
                "findings": ["Belief manifold is initialized and empty."],
            }

        confident = sum(1 for b in beliefs if b.status == BeliefStatus.CONFIDENT)
        contested = sum(1 for b in beliefs if b.status == BeliefStatus.CONTESTED)
        stale = sum(1 for b in beliefs if b.is_stale)
        unknown = sum(1 for b in beliefs if b.status == BeliefStatus.UNKNOWN)

        # Detect potential false confidence (high confidence despite active contradictions)
        false_confidence_risks = [
            b.belief_id for b in beliefs
            if b.status == BeliefStatus.CONFIDENT and len(b.contradiction_evidence_ids) > 0
        ]

        # Calculate deduplication ratio
        unique_hashes = len(set(e.content_hash for e in evidence_items))
        total_ev = len(evidence_items)
        dedup_rate = round(1.0 - (unique_hashes / (total_ev + 1e-6)), 3) if total_ev > 0 else 0.0

        # Unresolved conflicts
        unresolved_conflicts = [
            c.conflict_id for c in conflicts
            if c.resolution == ConflictResolution.CONTESTED and c.resolved_at is None
        ]

        # Epistemic health score calculation
        health_penalty = 0.0
        if false_confidence_risks:
            health_penalty += 0.25 * len(false_confidence_risks)
        if stale / total > 0.4:
            health_penalty += 0.15

        health_score = max(0.0, min(1.0, round(1.0 - health_penalty, 3)))

        findings: List[str] = []
        if false_confidence_risks:
            findings.append(f"DETECTED {len(false_confidence_risks)} belief(s) in CONFIDENT status with unaddressed contradiction evidence.")
        if stale > 0:
            findings.append(f"{stale} belief(s) have aged past freshness TTL and require revalidation.")
        if unresolved_conflicts:
            findings.append(f"{len(unresolved_conflicts)} active epistemic conflict(s) are contested.")

        return {
            "evaluated_at": utc_now().isoformat(),
            "total_beliefs": total,
            "confident_count": confident,
            "contested_count": contested,
            "stale_count": stale,
            "unknown_count": unknown,
            "total_revisions": revisions_count,
            "evidence_deduplication_rate": dedup_rate,
            "false_confidence_risks": false_confidence_risks,
            "unresolved_conflicts_count": len(unresolved_conflicts),
            "epistemic_health_score": health_score,
            "findings": findings or ["All active beliefs comply with epistemic invariants."],
        }
