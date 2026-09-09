"""Semantic assertion modeling, lifecycle states, and inference-fact segregation."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Dict, List, Optional
import uuid

from app.knowledge_graph.schemas import (
    AssertionSchema,
    AssertionStatus,
    ScopeType,
)


class InferenceFactViolationError(Exception):
    """Raised when an inferred assertion is improperly stored as verified fact without validation."""
    pass


class AssertionManager:
    """Manages semantic assertions, lifecycle transitions, and strict inference-fact separation."""

    def __init__(self) -> None:
        # assertion_id -> AssertionSchema
        self._assertions: Dict[str, AssertionSchema] = {}
        # subject (lower) -> list of assertion_ids
        self._subject_index: Dict[str, List[str]] = {}

    def create_assertion(
        self,
        subject: str,
        predicate: str,
        object_val: str,
        source: Optional[Dict[str, Any]] = None,
        confidence: float = 1.0,
        scope: ScopeType = ScopeType.PRIVATE,
        user_id: str = "default_user",
        is_inferred: bool = False,
        status: Optional[AssertionStatus] = None,
    ) -> AssertionSchema:
        """INVARIANT 13 & 14: Inferred relationships must be explicitly marked.

        Never store 'inferred' as 'known' (ACTIVE verified) without validation.
        """
        initial_status = status or (AssertionStatus.UNVERIFIED if is_inferred else AssertionStatus.ACTIVE)

        if is_inferred and initial_status == AssertionStatus.ACTIVE and confidence < 0.9:
            raise InferenceFactViolationError(
                f"Cannot store inferred assertion '{subject} {predicate} {object_val}' as active known fact without validation."
            )

        a_id = str(uuid.uuid4())
        assertion = AssertionSchema(
            assertion_id=a_id,
            subject=subject.strip(),
            predicate=predicate.strip(),
            object=object_val.strip(),
            source=source or {"source": "direct_input"},
            timestamp=datetime.now(UTC),
            confidence=min(max(confidence, 0.0), 1.0),
            status=initial_status,
            scope=scope,
            user_id=user_id,
            is_inferred=is_inferred,
        )

        self._assertions[a_id] = assertion
        self._subject_index.setdefault(subject.strip().lower(), []).append(a_id)

        return assertion

    def get_assertion(self, assertion_id: str) -> Optional[AssertionSchema]:
        return self._assertions.get(assertion_id)

    def find_by_subject(self, subject: str, user_id: Optional[str] = None) -> List[AssertionSchema]:
        sub_key = subject.strip().lower()
        a_ids = self._subject_index.get(sub_key, [])
        results = [self._assertions[aid] for aid in a_ids if aid in self._assertions]
        if user_id:
            results = [a for a in results if a.user_id == user_id]
        return results

    def update_status(self, assertion_id: str, new_status: AssertionStatus) -> AssertionSchema:
        assertion = self._assertions.get(assertion_id)
        if not assertion:
            raise ValueError(f"Assertion '{assertion_id}' not found.")
        assertion.status = new_status
        return assertion
