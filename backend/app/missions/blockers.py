"""Blocker Management, Prioritization, and Human Escalation Engine (Task 66)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from app.missions.schemas import (
    Blocker,
    BlockerSeverity,
    BlockerStatus,
    Mission,
    MissionHealth,
    MissionStatus,
)

logger = logging.getLogger("kairo.missions.blockers")


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class BlockerManager:
    """Manages operational blockers, priority ordering, and human escalation workflows."""

    def __init__(self) -> None:
        self._blockers: dict[str, Blocker] = {}

    def register_blocker(
        self,
        mission: Mission,
        blocker_type: str,
        description: str,
        severity: BlockerSeverity = BlockerSeverity.HIGH,
        impact_score: float = 0.7,
        owner: str = "system",
    ) -> Blocker:
        """Register a blocker and set mission health to BLOCKED (Spec 68, 69)."""
        blocker = Blocker(
            mission_id=mission.mission_id,
            blocker_type=blocker_type,
            description=description,
            severity=severity,
            impact_score=impact_score,
            owner=owner,
            status=BlockerStatus.DETECTED,
        )
        self._blockers[blocker.blocker_id] = blocker
        mission.blockers.append(blocker)

        # Update mission state
        if severity in (BlockerSeverity.HIGH, BlockerSeverity.CRITICAL):
            mission.health = MissionHealth.BLOCKED
            if mission.status == MissionStatus.RUNNING:
                mission.status = MissionStatus.BLOCKED

        logger.warning(
            "BLOCKER_DETECTED: id=%s mission=%s type=%s severity=%s",
            blocker.blocker_id,
            mission.mission_id,
            blocker_type,
            severity.value,
        )
        return blocker

    def resolve_blocker(self, blocker_id: str, resolution_notes: str) -> Blocker:
        """Mark a blocker as resolved (Spec 69)."""
        blocker = self._blockers.get(blocker_id)
        if not blocker:
            raise KeyError(f"Blocker '{blocker_id}' not found.")

        blocker.status = BlockerStatus.RESOLVED
        blocker.resolution = resolution_notes
        blocker.resolved_at = _now_utc()
        logger.info("BLOCKER_RESOLVED: id=%s notes=%s", blocker_id, resolution_notes)
        return blocker

    def prioritize_blockers(self, blockers: list[Blocker]) -> list[Blocker]:
        """Rank blockers by impact severity (Spec 70)."""
        severity_weight = {
            BlockerSeverity.CRITICAL: 1.0,
            BlockerSeverity.HIGH: 0.75,
            BlockerSeverity.MEDIUM: 0.5,
            BlockerSeverity.LOW: 0.25,
        }
        return sorted(
            blockers,
            key=lambda b: severity_weight.get(b.severity, 0.5) * 0.6 + b.impact_score * 0.4,
            reverse=True,
        )

    def generate_human_escalation(
        self,
        mission: Mission,
        blocker: Blocker,
        options: list[str] | None = None,
        recommended_action: str = "Grant additional resource quota or modify constraint",
    ) -> dict[str, Any]:
        """Formulate a comprehensive human escalation request (Spec 72).

        Contains: context, goal, current state, problem, options, risks, recommendation, required decision.
        """
        blocker.status = BlockerStatus.ESCALATED
        mission.status = MissionStatus.ESCALATED

        return {
            "escalation_id": f"esc_{blocker.blocker_id}",
            "mission_id": mission.mission_id,
            "mission_title": mission.title,
            "authority_scope": mission.authority_scope.value,
            "current_state": mission.status.value,
            "problem": {
                "blocker_id": blocker.blocker_id,
                "type": blocker.blocker_type,
                "description": blocker.description,
                "severity": blocker.severity.value,
            },
            "options": options
            or [
                "1. Approve temporary resource quota expansion",
                "2. Waive blocked dependency constraint",
                "3. Replan with alternative lower-risk strategy",
                "4. Abort mission gracefully",
            ],
            "risks": [
                "Continuing without resolution risks timeout or budget exhaustion.",
                "Waiving constraint may impact SLA guarantees.",
            ],
            "recommendation": recommended_action,
            "recommended_action": recommended_action,
            "required_decision": "Select an option to resume or cancel mission.",
            "escalated_at": _now_utc().isoformat(),
        }
