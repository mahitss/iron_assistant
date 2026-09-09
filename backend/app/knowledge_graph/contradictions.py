"""Contradiction detection across assertions and conflict preservation (INVARIANTS 93, 94, 100)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Dict, List, Optional
import uuid

from app.knowledge_graph.schemas import (
    AssertionSchema,
    AssertionStatus,
    ContradictionSchema,
)


class ContradictionDetector:
    """Detects conflicting assertions without silently losing contradictory evidence."""

    def __init__(self) -> None:
        # contradiction_id -> ContradictionSchema
        self._contradictions: Dict[str, ContradictionSchema] = {}

    def check_conflict(
        self,
        new_assertion: AssertionSchema,
        existing_assertions: List[AssertionSchema],
    ) -> Optional[ContradictionSchema]:
        """Checks if new_assertion contradicts any active existing assertion on same subject & predicate."""
        conflicting: List[AssertionSchema] = []

        for existing in existing_assertions:
            if existing.assertion_id == new_assertion.assertion_id:
                continue
            if existing.status != AssertionStatus.ACTIVE:
                continue

            # Same subject and predicate, but differing object
            if (
                existing.subject.lower() == new_assertion.subject.lower()
                and existing.predicate.lower() == new_assertion.predicate.lower()
                and existing.object.lower() != new_assertion.object.lower()
            ):
                conflicting.append(existing)

        if not conflicting:
            return None

        cid = str(uuid.uuid4())
        record = ContradictionSchema(
            contradiction_id=cid,
            subject=new_assertion.subject,
            conflicting_assertions=[
                {
                    "assertion_id": new_assertion.assertion_id,
                    "predicate": new_assertion.predicate,
                    "object": new_assertion.object,
                    "confidence": new_assertion.confidence,
                    "source": new_assertion.source,
                    "timestamp": new_assertion.timestamp.isoformat(),
                }
            ] + [
                {
                    "assertion_id": ex.assertion_id,
                    "predicate": ex.predicate,
                    "object": ex.object,
                    "confidence": ex.confidence,
                    "source": ex.source,
                    "timestamp": ex.timestamp.isoformat(),
                }
                for ex in conflicting
            ],
            detected_at=datetime.now(UTC),
            status="DETECTED",
            user_id=new_assertion.user_id,
        )

        self._contradictions[cid] = record
        return record

    def list_contradictions(self, user_id: Optional[str] = None) -> List[ContradictionSchema]:
        results = list(self._contradictions.values())
        if user_id:
            results = [c for c in results if c.user_id == user_id]
        return results

    def get_contradiction(self, contradiction_id: str) -> Optional[ContradictionSchema]:
        return self._contradictions.get(contradiction_id)
