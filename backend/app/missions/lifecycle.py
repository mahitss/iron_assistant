"""Mission State Machine, Transition Guards, and Lifecycle Control (Task 66)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.missions.safety import MissionSafetyError
from app.missions.schemas import (
    Mission,
    MissionCheckpoint,
    MissionHealth,
    MissionStatus,
)

logger = logging.getLogger("kairo.missions.lifecycle")


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class MissionStateMachine:
    """Manages the 16 canonical lifecycle states of a self-directed mission (Spec 25)."""

    # Allowed transitions graph
    _TRANSITIONS: dict[MissionStatus, set[MissionStatus]] = {
        MissionStatus.DRAFT: {MissionStatus.VALIDATING, MissionStatus.CANCELLED},
        MissionStatus.VALIDATING: {
            MissionStatus.READY,
            MissionStatus.DRAFT,
            MissionStatus.ESCALATED,
            MissionStatus.CANCELLED,
            MissionStatus.FAILED,
        },
        MissionStatus.READY: {
            MissionStatus.PLANNING,
            MissionStatus.WAITING_FOR_RESOURCES,
            MissionStatus.WAITING_FOR_APPROVAL,
            MissionStatus.RUNNING,
            MissionStatus.PAUSED,
            MissionStatus.CANCELLED,
        },
        MissionStatus.PLANNING: {
            MissionStatus.READY,
            MissionStatus.WAITING_FOR_RESOURCES,
            MissionStatus.WAITING_FOR_APPROVAL,
            MissionStatus.RUNNING,
            MissionStatus.BLOCKED,
            MissionStatus.CANCELLED,
        },
        MissionStatus.WAITING_FOR_RESOURCES: {
            MissionStatus.RUNNING,
            MissionStatus.BLOCKED,
            MissionStatus.PAUSED,
            MissionStatus.CANCELLED,
        },
        MissionStatus.WAITING_FOR_APPROVAL: {
            MissionStatus.RUNNING,
            MissionStatus.BLOCKED,
            MissionStatus.ESCALATED,
            MissionStatus.CANCELLED,
            MissionStatus.REPLANNING,
        },
        MissionStatus.RUNNING: {
            MissionStatus.PAUSED,
            MissionStatus.BLOCKED,
            MissionStatus.REPLANNING,
            MissionStatus.VERIFYING,
            MissionStatus.ESCALATED,
            MissionStatus.FAILED,
            MissionStatus.CANCELLED,
            MissionStatus.EXPIRED,
        },
        MissionStatus.PAUSED: {
            MissionStatus.RUNNING,
            MissionStatus.VALIDATING,
            MissionStatus.REPLANNING,
            MissionStatus.CANCELLED,
            MissionStatus.EXPIRED,
        },
        MissionStatus.BLOCKED: {
            MissionStatus.RUNNING,
            MissionStatus.REPLANNING,
            MissionStatus.ESCALATED,
            MissionStatus.CANCELLED,
            MissionStatus.FAILED,
        },
        MissionStatus.REPLANNING: {
            MissionStatus.READY,
            MissionStatus.RUNNING,
            MissionStatus.BLOCKED,
            MissionStatus.WAITING_FOR_APPROVAL,
            MissionStatus.CANCELLED,
        },
        MissionStatus.VERIFYING: {
            MissionStatus.COMPLETED,
            MissionStatus.PARTIALLY_COMPLETED,
            MissionStatus.REPLANNING,
            MissionStatus.FAILED,
            MissionStatus.ESCALATED,
        },
        MissionStatus.ESCALATED: {
            MissionStatus.RUNNING,
            MissionStatus.PLANNING,
            MissionStatus.PAUSED,
            MissionStatus.CANCELLED,
            MissionStatus.FAILED,
        },
        MissionStatus.COMPLETED: set(),  # Terminal
        MissionStatus.PARTIALLY_COMPLETED: set(),  # Terminal
        MissionStatus.FAILED: set(),  # Terminal
        MissionStatus.CANCELLED: set(),  # Terminal
        MissionStatus.EXPIRED: {MissionStatus.VALIDATING, MissionStatus.CANCELLED},
    }

    @classmethod
    def can_transition(cls, current: MissionStatus, target: MissionStatus) -> bool:
        return target in cls._TRANSITIONS.get(current, set())

    @classmethod
    def transition(
        cls,
        mission: Mission,
        target: MissionStatus,
        reason: str = "",
        actor: str = "system",
    ) -> Mission:
        """Execute a state transition with guard checks and checkpoint recording."""
        # Check expiration (Spec 50)
        if (
            mission.expires_at
            and _now_utc() > mission.expires_at
            and target not in (MissionStatus.EXPIRED, MissionStatus.CANCELLED)
        ):
            logger.warning(
                "Mission %s expired at %s; forcing EXPIRED state", mission.mission_id, mission.expires_at
            )
            target = MissionStatus.EXPIRED

        if not cls.can_transition(mission.status, target):
            raise MissionSafetyError(
                f"Illegal State Transition: Cannot move mission '{mission.mission_id}' "
                f"from '{mission.status.value}' to '{target.value}'."
            )

        old_status = mission.status
        mission.status = target
        mission.updated_at = _now_utc()
        mission.version += 1

        # Health mapping
        if target == MissionStatus.RUNNING:
            mission.health = MissionHealth.ON_TRACK
        elif target == MissionStatus.BLOCKED:
            mission.health = MissionHealth.BLOCKED
        elif target == MissionStatus.COMPLETED:
            mission.health = MissionHealth.COMPLETED
        elif target == MissionStatus.FAILED:
            mission.health = MissionHealth.FAILED

        # Record checkpoint (Spec 26)
        checkpoint = MissionCheckpoint(
            mission_id=mission.mission_id,
            state=target,
            progress_pct=mission.progress_pct,
            evidence=[f"Transitioned from {old_status.value} to {target.value}. Reason: {reason}"],
            next_steps=[f"Proceed in state {target.value}"],
        )
        mission.checkpoints.append(checkpoint)

        logger.info(
            "MISSION_TRANSITION: id=%s %s -> %s actor=%s reason=%s",
            mission.mission_id,
            old_status.value,
            target.value,
            actor,
            reason,
        )
        return mission

    @classmethod
    def revalidate_and_resume(cls, mission: Mission, is_world_valid: bool = True) -> Mission:
        """Revalidate world state and resources before resuming paused/stale missions (Spec 48, 49)."""
        if mission.status != MissionStatus.PAUSED:
            raise MissionSafetyError("Only PAUSED missions can be resumed via revalidate_and_resume.")

        if not is_world_valid:
            logger.warning(
                "World state or assumptions changed during pause for mission %s", mission.mission_id
            )
            return cls.transition(
                mission,
                MissionStatus.REPLANNING,
                reason="World state invalidation detected upon resumption",
            )

        return cls.transition(mission, MissionStatus.RUNNING, reason="State revalidated, resuming execution")
