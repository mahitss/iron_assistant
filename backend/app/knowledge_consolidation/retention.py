"""Multi-attribute retention evaluator for KAIRO knowledge (Task 92 Phase 12).

Guarantees:
- Does not retain everything forever
- Bounded retention considering utility, importance, freshness, and contradiction
- Explicit retention outcomes: RETAIN, UPDATE, MERGE, SUPERSEDE, ARCHIVE, FORGET, REVALIDATE, ESCALATE
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.knowledge_consolidation.models import (
    MemoryEntity,
    MemoryStatus,
    RetentionAction,
    RetentionDecision,
    generate_id,
)


class RetentionEngine:
    """Evaluates memory records to determine lifecycle retention actions."""

    def evaluate_retention(
        self,
        memory: MemoryEntity,
        evidence_summary: dict[str, Any],
        temporal_engine: Any,
        at_time: datetime | None = None,
    ) -> RetentionDecision:
        """Evaluate multi-attribute criteria and produce a deterministic retention decision."""
        now = at_time or datetime.now(UTC)

        # 1. Terminal / Already Forgotten
        if memory.status == MemoryStatus.FORGOTTEN:
            return RetentionDecision(
                decision_id=generate_id("ret"),
                memory_id=memory.memory_id,
                action=RetentionAction.FORGET,
                reason="Memory is in terminal FORGOTTEN status",
                importance_score=memory.importance,
                utility_score=0.0,
            )

        # 2. Invalidated or Superseded -> Candidate for Archive
        if memory.status in (MemoryStatus.INVALIDATED, MemoryStatus.SUPERSEDED):
            return RetentionDecision(
                decision_id=generate_id("ret"),
                memory_id=memory.memory_id,
                action=RetentionAction.ARCHIVE,
                reason=f"Memory is {memory.status.value}; eligible for archiving",
                importance_score=memory.importance,
                utility_score=0.1,
            )

        # 3. Staleness Evaluation
        is_stale, freshness_label = temporal_engine.evaluate_staleness(memory, at_time=now)
        if is_stale or memory.status == MemoryStatus.STALE:
            # High importance items warrant autonomous revalidation rather than immediate forgetting
            if memory.importance >= 0.7:
                return RetentionDecision(
                    decision_id=generate_id("ret"),
                    memory_id=memory.memory_id,
                    action=RetentionAction.REVALIDATE,
                    reason=f"High-importance memory is {freshness_label}; scheduled for revalidation",
                    importance_score=memory.importance,
                    utility_score=0.7,
                )
            else:
                return RetentionDecision(
                    decision_id=generate_id("ret"),
                    memory_id=memory.memory_id,
                    action=RetentionAction.ARCHIVE,
                    reason=f"Stale low-utility memory ({freshness_label}); archiving",
                    importance_score=memory.importance,
                    utility_score=0.2,
                )

        # 4. Contradiction Flag
        if memory.status == MemoryStatus.CONFLICTED or evidence_summary.get("has_contradiction"):
            return RetentionDecision(
                decision_id=generate_id("ret"),
                memory_id=memory.memory_id,
                action=RetentionAction.ESCALATE,
                reason="Unresolved contradiction detected; requires conflict resolution or escalation",
                importance_score=memory.importance,
                utility_score=0.5,
            )

        # 5. Low Utility & Low Importance Expiry
        if memory.importance < 0.2 and memory.confidence < 0.4:
            return RetentionDecision(
                decision_id=generate_id("ret"),
                memory_id=memory.memory_id,
                action=RetentionAction.ARCHIVE,
                reason="Low confidence and low importance; eligible for archival",
                importance_score=memory.importance,
                utility_score=0.1,
            )

        # 6. Default: Retain Active Knowledge
        return RetentionDecision(
            decision_id=generate_id("ret"),
            memory_id=memory.memory_id,
            action=RetentionAction.RETAIN,
            reason="Active, validated knowledge with positive utility score",
            importance_score=memory.importance,
            utility_score=round(memory.confidence * memory.relevance, 3),
        )
