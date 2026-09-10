"""Attention prioritization, flapping detection, and alert storm dampening (Task 60)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.situational_awareness.schemas import (
    AttentionItem,
    Situation,
    SituationSeverity,
    SituationStatus,
)

logger = logging.getLogger(__name__)


class AttentionEngine:
    """Calculates composite attention priority, detects flapping, and prevents alert storms."""

    def __init__(self, flapping_threshold: int = 3, flapping_window_seconds: float = 300.0) -> None:
        self._flapping_threshold = flapping_threshold
        self._flapping_window = flapping_window_seconds
        # History: situation_id -> list of status transition timestamps
        self._transition_history: dict[str, list[datetime]] = {}

    def score_attention(self, situation: Situation) -> AttentionItem:
        """Calculate composite attention priority for a situation.

        Invariant 74: Attention != Action. High attention does not mean automatic execution.
        """
        severity_weights = {
            SituationSeverity.CRITICAL: 1.0,
            SituationSeverity.HIGH: 0.8,
            SituationSeverity.MEDIUM: 0.5,
            SituationSeverity.LOW: 0.3,
            SituationSeverity.INFO: 0.1,
        }
        sev_w = severity_weights.get(situation.severity, 0.5)

        # Impact weight: based on affected plans, goals, and resources
        total_impacted = (
            len(situation.affected_plans) + len(situation.affected_goals) + len(situation.affected_resources)
        )
        impact_w = min(1.0, total_impacted * 0.2)

        # Urgency: higher if UNCONFIRMED or MITIGATING
        urgency_w = 0.9 if situation.status in (SituationStatus.DETECTED, SituationStatus.MITIGATING) else 0.4

        # Composite priority (0.0 to 1.0)
        composite = (sev_w * 0.5) + (impact_w * 0.3) + (urgency_w * 0.2)
        requires_human = (
            situation.severity in (SituationSeverity.HIGH, SituationSeverity.CRITICAL)
            or len(situation.affected_goals) > 0
        )

        item = AttentionItem(
            situation_id=situation.situation_id,
            title=situation.title,
            severity=situation.severity,
            urgency=round(urgency_w, 2),
            composite_priority=round(composite, 2),
            requires_human_action=requires_human,
        )
        return item

    def record_transition_and_check_flapping(
        self,
        situation_id: str,
        new_status: SituationStatus,
    ) -> bool:
        """Record status transition and detect rapid oscillations (flapping)."""
        now = datetime.now(timezone.utc)
        if situation_id not in self._transition_history:
            self._transition_history[situation_id] = []

        history = self._transition_history[situation_id]
        history.append(now)

        # Keep only timestamps within flapping window
        history = [t for t in history if (now - t).total_seconds() <= self._flapping_window]
        self._transition_history[situation_id] = history

        is_flapping = len(history) >= self._flapping_threshold
        if is_flapping:
            logger.warning(
                "FLAPPING_DETECTED: Situation '%s' has transitioned %d times in %.0fs window.",
                situation_id,
                len(history),
                self._flapping_window,
            )
        return is_flapping


attention_engine = AttentionEngine()
