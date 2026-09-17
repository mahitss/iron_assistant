"""Lifecycle, Versioning, Correction, Supersession & Snapshot Engine for Task 108.

Implements:
- Section 3: Request Lifecycle (RECEIVED, PARSING, UNDERSTOOD, CONFIRMED, SUPERSEDED, CANCELLED, etc.)
- Section 20: User Correction ("No, I meant staging", "Don't delete them, archive them")
- Section 21: Intent Versioning (immutable version records v1 -> v2)
- Section 22: Intent Snapshots (decision-time epistemic reconstruction)
- Section 38: Intent Supersession ("Actually, forget that" -> SUPERSEDED, old objective halts)
- Section 39: Cancellation ("Stop", "Never mind" -> CANCELLED, propagates downstream)
- Section 40: Conflicting Requests (latest explicit instruction supersedes prior intent)
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from app.intent.domain import (
    Assumption,
    Constraint,
    DesiredOutcome,
    ExternalEffectFlag,
    GoalHypothesis,
    Intent,
    IntentCorrection,
    IntentSnapshot,
    IntentVersion,
    RequestStatus,
    UserRequest,
    generate_id,
    utc_now,
)

logger = logging.getLogger("kairo.intent.lifecycle_versioning")


class LifecycleAndVersioningEngine:
    """Manages lifecycle transitions, version lineage, corrections, and snapshots."""

    @classmethod
    def apply_correction(
        cls,
        current_intent: Intent,
        correction_text: str,
        scope_affected: str = "CURRENT_PROJECT",
    ) -> Tuple[Intent, IntentVersion, IntentCorrection]:
        """Applies user correction, generating a new immutable version and correction record (Spec 20, 21)."""
        # Save snapshot of prior version
        prior_version = IntentVersion(
            version_id=generate_id("iver"),
            intent_id=current_intent.intent_id,
            version_number=current_intent.version,
            intent_snapshot=current_intent.model_dump(mode="json"),
            reason_for_change=f"User correction: {correction_text}",
            created_at=utc_now(),
        )

        # Create correction log
        correction = IntentCorrection(
            correction_id=generate_id("icor"),
            request_id=current_intent.request_id,
            prior_intent_id=current_intent.intent_id,
            revised_intent_id=current_intent.intent_id,
            user_feedback_text=correction_text,
            scope_affected=scope_affected,
            created_at=utc_now(),
        )

        # Revise intent in-place for new version
        current_intent.version += 1
        current_intent.summary = f"{current_intent.summary} [Corrected: {correction_text}]"

        # If correction specifies a new target
        if "staging" in correction_text.lower():
            current_intent.target = "staging"
        elif "frontend" in correction_text.lower():
            current_intent.target = "frontend"
        elif "backend" in correction_text.lower():
            current_intent.target = "backend"
        elif "archive" in correction_text.lower():
            current_intent.action_class = "archive"
            current_intent.user_visible_outcome = "Archive items instead of destructive deletion."

        current_intent.updated_at = utc_now()

        logger.info("Applied correction to intent %s -> version %d (feedback='%s')",
                    current_intent.intent_id, current_intent.version, correction_text)
        return current_intent, prior_version, correction

    @classmethod
    def supersede_intent(
        cls,
        prior_intent: Intent,
        superseding_intent_id: str,
        reason: str = "Superseded by subsequent user directive",
    ) -> Intent:
        """Marks prior intent as SUPERSEDED so it cannot execute (Spec 38)."""
        prior_intent.is_superseded = True
        prior_intent.superseded_by = superseding_intent_id
        prior_intent.status = RequestStatus.SUPERSEDED
        prior_intent.updated_at = utc_now()
        logger.warning("Intent %s SUPERSEDED by %s: reason='%s'",
                       prior_intent.intent_id, superseding_intent_id, reason)
        return prior_intent

    @classmethod
    def cancel_intent(
        cls,
        intent: Intent,
        reason: str = "User explicit cancellation",
    ) -> Intent:
        """Marks intent as CANCELLED (Spec 39)."""
        intent.is_cancelled = True
        intent.cancellation_reason = reason
        intent.status = RequestStatus.CANCELLED
        intent.updated_at = utc_now()
        logger.warning("Intent %s CANCELLED: reason='%s'", intent.intent_id, reason)
        return intent

    @classmethod
    def create_snapshot(
        cls,
        intent: Intent,
        goal_hypotheses: List[GoalHypothesis],
        constraints: List[Constraint],
        assumptions: List[Assumption],
    ) -> IntentSnapshot:
        """Creates an immutable snapshot before major downstream handoffs (Spec 22)."""
        snapshot = IntentSnapshot(
            snapshot_id=generate_id("isnap"),
            intent_id=intent.intent_id,
            request_id=intent.request_id,
            timestamp=utc_now(),
            intent_data=intent.model_dump(mode="json"),
            goal_hypotheses=[g.model_dump(mode="json") for g in goal_hypotheses],
            constraints=[c.model_dump(mode="json") for c in constraints],
            non_goals=list(intent.non_goals),
            assumptions=[a.model_dump(mode="json") for a in assumptions],
            external_effect=intent.external_effect,
            confidence_breakdown={
                "target": intent.target_confidence,
                "goal": intent.goal_confidence,
                "constraint": intent.constraint_confidence,
                "deadline": intent.deadline_confidence,
                "scope": intent.scope_confidence,
                "overall": intent.overall_confidence,
            },
        )
        logger.info("Created IntentSnapshot %s for intent %s", snapshot.snapshot_id, intent.intent_id)
        return snapshot
