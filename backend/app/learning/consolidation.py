"""Experience and lesson consolidation with contradiction safety (INVARIANTS 105-107)."""

from __future__ import annotations

from typing import Any
from app.learning.schemas import LessonSchema, LessonStatus


class ContradictoryConsolidationError(Exception):
    """Raised when an attempt is made to merge mutually contradictory lessons."""
    pass


class ExperienceConsolidator:
    """Safely consolidates redundant experiences and lessons while guarding against contradictory merges."""

    @classmethod
    def are_contradictory(cls, statement_a: str, statement_b: str) -> bool:
        """INVARIANT 106: Heuristic check for direct contradictory statements."""
        sa = statement_a.lower().strip()
        sb = statement_b.lower().strip()

        # Obvious negative markers
        contradiction_pairs = [
            ("always use", "never use"),
            ("do not use", "always use"),
            ("enable", "disable"),
            ("safe to run", "unsafe to run"),
            ("requires approval", "does not require approval"),
        ]
        for pos, neg in contradiction_pairs:
            if (pos in sa and neg in sb) or (neg in sa and pos in sb):
                return True
        return False

    @classmethod
    def consolidate_lessons(cls, target_lesson: LessonSchema, candidate_lesson: LessonSchema) -> LessonSchema:
        """INVARIANT 105 & 106: Consolidates candidate into target lesson without losing evidence.
        Rejects contradictory consolidation.
        """
        if cls.are_contradictory(target_lesson.statement, candidate_lesson.statement):
            raise ContradictoryConsolidationError(
                f"INVARIANT 106: Cannot merge contradictory lessons:\n"
                f"A: '{target_lesson.statement}'\n"
                f"B: '{candidate_lesson.statement}'"
            )

        # Merge supporting experiences uniquely
        merged_exps = set(target_lesson.source_experiences) | set(candidate_lesson.source_experiences)
        target_lesson.source_experiences = list(merged_exps)

        # Merge evidence items
        target_lesson.evidence.extend(candidate_lesson.evidence)

        # Reinforce target lesson
        target_lesson.reinforcement_count += candidate_lesson.reinforcement_count
        target_lesson.confidence = min(max(target_lesson.confidence, candidate_lesson.confidence) + 0.03, 1.0)
        target_lesson.decay_score = 1.0

        # Mark candidate as superseded / consolidated
        candidate_lesson.status = LessonStatus.SUPERSEDED
        candidate_lesson.validity = {
            "status": "CONSOLIDATED",
            "merged_into": target_lesson.lesson_id,
        }

        return target_lesson
