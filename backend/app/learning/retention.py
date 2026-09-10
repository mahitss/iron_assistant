"""Data retention, authorized deletion, and derived artifact cleanup (INVARIANTS 173-175, 233)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from app.learning.experiences import ExperienceManager
from app.learning.lessons import LessonExtractor


class LearningRetentionManager:
    """Enforces retention windows, purges expired experiences, and cascades deletion to derived lessons."""

    def __init__(self, default_retention_days: int = 90) -> None:
        self.retention_period = timedelta(days=default_retention_days)

    def purge_expired_experiences(self, experience_mgr: ExperienceManager) -> int:
        """INVARIANT 173: Purges raw experiences older than the retention threshold."""
        now = datetime.now(UTC)
        cutoff = now - self.retention_period
        all_exps = experience_mgr.list_experiences()

        purged_count = 0
        for exp in all_exps:
            if exp.timestamp < cutoff and exp.status != "CONSOLIDATED":
                experience_mgr.delete_experience(exp.experience_id)
                purged_count += 1
        return purged_count

    def execute_authorized_deletion(
        self,
        experience_id: str,
        experience_mgr: ExperienceManager,
        lesson_extractor: LessonExtractor | None = None,
        cascade: bool = True,
    ) -> dict[str, Any]:
        """INVARIANT 174 & 175: Deletes experience and cascades deletion to derived lessons referencing it."""
        exp_deleted = experience_mgr.delete_experience(experience_id)
        cascaded_lessons_deleted = 0

        if cascade and lesson_extractor:
            lessons = lesson_extractor.list_lessons()
            for lsn in lessons:
                if experience_id in lsn.source_experiences:
                    lsn.source_experiences.remove(experience_id)
                    # If this was the sole supporting experience, remove or weaken the lesson
                    if not lsn.source_experiences and not lsn.evidence:
                        lesson_extractor.delete_lesson(lsn.lesson_id)
                        cascaded_lessons_deleted += 1

        return {
            "experience_id": experience_id,
            "experience_deleted": exp_deleted,
            "cascaded_lessons_deleted": cascaded_lessons_deleted,
            "timestamp": datetime.now(UTC).isoformat(),
        }
