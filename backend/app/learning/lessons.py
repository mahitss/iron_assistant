"""Lesson extraction, empirical evidence grounding, and lifecycle management (INVARIANTS 11-13, 102-104, 120)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
import uuid

from app.learning.schemas import GeneralizationScope, LessonSchema, LessonStatus, LessonType


class LessonExtractor:
    """Extracts, reinforces, and supersedes evidence-grounded lessons from experiences."""

    def __init__(self) -> None:
        # lesson_id -> LessonSchema
        self._lessons: dict[str, LessonSchema] = {}

    def extract_lesson(
        self,
        statement: str,
        lesson_type: LessonType,
        source_experiences: list[str],
        evidence: list[dict[str, Any]],
        confidence: float = 0.8,
        scope: GeneralizationScope = GeneralizationScope.PROJECT,
        validity: dict[str, Any] | None = None,
        status: LessonStatus = LessonStatus.CANDIDATE,
    ) -> LessonSchema:
        """INVARIANT 11, 13, 120: Creates a structured lesson strictly requiring empirical evidence.
        Never fabricates lessons without source experiences.
        """
        clean_statement = statement.strip()
        if not clean_statement:
            raise ValueError("Lesson statement cannot be empty.")
        if not source_experiences and not evidence:
            raise ValueError("INVARIANT 120: Cannot extract lesson without supporting experience or empirical evidence.")

        lid = f"lsn_{uuid.uuid4().hex[:12]}"
        now = datetime.now(UTC)
        lesson = LessonSchema(
            lesson_id=lid,
            statement=clean_statement,
            lesson_type=lesson_type,
            source_experiences=list(source_experiences),
            evidence=list(evidence),
            confidence=min(max(confidence, 0.1), 1.0),
            scope=scope,
            validity=validity or {"status": "VALID"},
            status=status,
            reinforcement_count=1,
            decay_score=1.0,
            created_at=now,
            updated_at=now,
        )
        self._lessons[lid] = lesson
        return lesson

    def reinforce_lesson(self, lesson_id: str, new_evidence: dict[str, Any]) -> LessonSchema:
        """INVARIANT 100: Repeated verified success increases relevance and reinforcement count."""
        lesson = self._lessons.get(lesson_id)
        if not lesson:
            raise ValueError(f"Lesson '{lesson_id}' not found.")

        lesson.reinforcement_count += 1
        lesson.confidence = min(lesson.confidence + 0.05, 1.0)
        lesson.decay_score = 1.0  # Reset decay upon reinforcement
        lesson.evidence.append(new_evidence)
        lesson.updated_at = datetime.now(UTC)
        return lesson

    def supersede_lesson(self, old_lesson_id: str, new_lesson_id: str, reason: str) -> None:
        """INVARIANT 103: Supersedes older lesson with newer validated lesson."""
        old = self._lessons.get(old_lesson_id)
        if not old:
            raise ValueError(f"Old lesson '{old_lesson_id}' not found.")
        new = self._lessons.get(new_lesson_id)
        if not new:
            raise ValueError(f"New lesson '{new_lesson_id}' not found.")

        old.status = LessonStatus.SUPERSEDED
        old.validity = {
            "status": "SUPERSEDED",
            "superseded_by": new_lesson_id,
            "reason": reason,
            "superseded_at": datetime.now(UTC).isoformat(),
        }
        old.updated_at = datetime.now(UTC)

    def get_lesson(self, lesson_id: str) -> LessonSchema | None:
        return self._lessons.get(lesson_id)

    def list_lessons(
        self,
        lesson_type: LessonType | None = None,
        scope: GeneralizationScope | None = None,
        status: LessonStatus | None = None,
    ) -> list[LessonSchema]:
        results = list(self._lessons.values())
        if lesson_type:
            results = [l for l in results if l.lesson_type == lesson_type.value or l.lesson_type == lesson_type]
        if scope:
            results = [l for l in results if l.scope == scope.value or l.scope == scope]
        if status:
            results = [l for l in results if l.status == status.value or l.status == status]
        return results

    def delete_lesson(self, lesson_id: str) -> bool:
        """INVARIANT 175: Authorized deletion of derived lesson."""
        if lesson_id in self._lessons:
            del self._lessons[lesson_id]
            return True
        return False
