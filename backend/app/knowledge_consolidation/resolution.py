"""Conflict resolution engine for KAIRO knowledge (Task 92 Phase 9).

Guarantees:
- Never resolves based solely on 'the newest model output'
- Requires strong corroborating evidence or explicit authoritative verification
- If evidence is insufficient or ambiguous, retains CONFLICTED state
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.knowledge_consolidation.models import (
    CertaintyState,
    MemoryConflict,
    MemoryEntity,
    MemoryStatus,
    ProvenanceSourceType,
)


class ConflictResolutionEngine:
    """Evaluates competing claims using multi-factor evidence and authority."""

    def resolve_conflict(
        self,
        conflict: MemoryConflict,
        memory_a: MemoryEntity,
        memory_b: MemoryEntity,
        evidence_manager: Any,
        strategy: str = "stronger_evidence",
        actor: str = "kairo_system",
        override_winner_id: str | None = None,
    ) -> tuple[bool, str]:
        """Attempt to resolve a conflict.

        Returns: (resolved: bool, explanation: str)
        """
        now = datetime.now(UTC)

        # 1. Explicit User / Operator Correction
        if strategy == "user_correction" and override_winner_id:
            winner = memory_a if memory_a.memory_id == override_winner_id else memory_b
            loser = memory_b if winner.memory_id == memory_a.memory_id else memory_a

            winner.status = MemoryStatus.ACTIVE
            winner.certainty = CertaintyState.KNOWN
            loser.status = MemoryStatus.SUPERSEDED
            loser.superseded_by = winner.memory_id
            winner.supersedes = loser.memory_id

            conflict.status = "RESOLVED"
            conflict.resolution_strategy = "user_correction"
            conflict.resolution_winner_id = winner.memory_id
            conflict.resolved_by = actor
            conflict.resolved_at = now
            return True, f"Conflict resolved by explicit user correction favoring memory '{winner.memory_id}'"

        # 2. Source Authority Check (System Verified or User Asserted > Inferred)
        auth_scores = {
            ProvenanceSourceType.SYSTEM_VERIFIED: 1.0,
            ProvenanceSourceType.USER_ASSERTED: 0.95,
            ProvenanceSourceType.OBSERVED: 0.85,
            ProvenanceSourceType.EXTERNALLY_SOURCED: 0.80,
            ProvenanceSourceType.DERIVED: 0.70,
            ProvenanceSourceType.INFERRED: 0.50,
            ProvenanceSourceType.MODEL_GENERATED: 0.40,
        }

        src_a_type = memory_a.provenance.source_type if memory_a.provenance else ProvenanceSourceType.OBSERVED
        src_b_type = memory_b.provenance.source_type if memory_b.provenance else ProvenanceSourceType.OBSERVED

        score_a = auth_scores.get(src_a_type, 0.5) * memory_a.confidence
        score_b = auth_scores.get(src_b_type, 0.5) * memory_b.confidence

        # Incorporate grounded evidence count & reliability
        ev_summary_a = evidence_manager.summarize_evidence_balance(memory_a.memory_id)
        ev_summary_b = evidence_manager.summarize_evidence_balance(memory_b.memory_id)

        total_score_a = score_a + ev_summary_a["supporting_weight"]
        total_score_b = score_b + ev_summary_b["supporting_weight"]

        # 3. Margin threshold: Must be decisive (> 0.4 delta) to resolve automatically
        margin = abs(total_score_a - total_score_b)
        if margin >= 0.4:
            winner = memory_a if total_score_a > total_score_b else memory_b
            loser = memory_b if winner.memory_id == memory_a.memory_id else memory_a

            winner.status = MemoryStatus.ACTIVE
            winner.certainty = CertaintyState.KNOWN
            loser.status = MemoryStatus.SUPERSEDED
            loser.superseded_by = winner.memory_id
            winner.supersedes = loser.memory_id

            conflict.status = "RESOLVED"
            conflict.resolution_strategy = "decisive_evidence_authority"
            conflict.resolution_winner_id = winner.memory_id
            conflict.resolved_by = actor
            conflict.resolved_at = now
            return True, f"Decisive resolution: memory '{winner.memory_id}' score ({total_score_a if winner == memory_a else total_score_b:.2f}) over '{loser.memory_id}' ({total_score_b if winner == memory_a else total_score_a:.2f})"

        # If inconclusive: retain CONFLICTED!
        return False, f"Inconclusive evidence margin ({margin:.2f} < 0.4). Conflict retained as unresolved."
