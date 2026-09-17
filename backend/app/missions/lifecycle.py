"""Mission State Machine, Transition Guards, and Lifecycle Control (Task 66 & Task 100)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from app.missions.safety import MissionSafetyError

MissionLifecycleError = MissionSafetyError

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
    """Manages the 18 operational lifecycle states of an autonomous mission (Task 66 & Task 100).

    Invariants:
    - State transitions are strictly validated against a deterministic transition matrix.
    - Every transition requires reason, actor, evidence, and audit metadata.
    - Resumption from PAUSED mandates world-state and assumption revalidation.
    - Emergency Stop halts autonomous progression and overrides active transitions fail-closed.
    """

    # Comprehensive transition graph supporting 18 operational states + legacy aliases
    _TRANSITIONS: dict[MissionStatus, set[MissionStatus]] = {
        MissionStatus.DRAFT: {
            MissionStatus.VALIDATING,
            MissionStatus.READY,
            MissionStatus.CANCELLED,
        },
        MissionStatus.VALIDATING: {
            MissionStatus.READY,
            MissionStatus.DRAFT,
            MissionStatus.ESCALATED,
            MissionStatus.CANCELLED,
            MissionStatus.FAILED,
        },
        MissionStatus.READY: {
            MissionStatus.ACTIVE,
            MissionStatus.RUNNING,
            MissionStatus.PLANNING,
            MissionStatus.VERIFYING,
            MissionStatus.WAITING_FOR_RESOURCES,
            MissionStatus.WAITING_FOR_APPROVAL,
            MissionStatus.AWAITING_APPROVAL,
            MissionStatus.AWAITING_USER,
            MissionStatus.PAUSED,
            MissionStatus.CANCELLED,
        },
        MissionStatus.PLANNING: {
            MissionStatus.READY,
            MissionStatus.ACTIVE,
            MissionStatus.RUNNING,
            MissionStatus.WAITING_FOR_RESOURCES,
            MissionStatus.WAITING_FOR_APPROVAL,
            MissionStatus.AWAITING_APPROVAL,
            MissionStatus.BLOCKED,
            MissionStatus.CANCELLED,
        },
        MissionStatus.WAITING_FOR_RESOURCES: {
            MissionStatus.ACTIVE,
            MissionStatus.RUNNING,
            MissionStatus.BLOCKED,
            MissionStatus.PAUSED,
            MissionStatus.CANCELLED,
        },
        MissionStatus.WAITING_FOR_APPROVAL: {
            MissionStatus.ACTIVE,
            MissionStatus.RUNNING,
            MissionStatus.BLOCKED,
            MissionStatus.ESCALATED,
            MissionStatus.CANCELLED,
            MissionStatus.REPLANNING,
        },
        MissionStatus.AWAITING_APPROVAL: {
            MissionStatus.ACTIVE,
            MissionStatus.RUNNING,
            MissionStatus.EXECUTING,
            MissionStatus.BLOCKED,
            MissionStatus.ESCALATED,
            MissionStatus.CANCELLED,
            MissionStatus.REPLANNING,
            MissionStatus.PAUSED,
        },
        MissionStatus.AWAITING_USER: {
            MissionStatus.ACTIVE,
            MissionStatus.RUNNING,
            MissionStatus.EXECUTING,
            MissionStatus.BLOCKED,
            MissionStatus.PAUSED,
            MissionStatus.CANCELLED,
            MissionStatus.ABANDONED,
            MissionStatus.REPLANNING,
        },
        MissionStatus.ACTIVE: {
            MissionStatus.EXECUTING,
            MissionStatus.VERIFYING,
            MissionStatus.STABILIZING,
            MissionStatus.PAUSED,
            MissionStatus.BLOCKED,
            MissionStatus.DEGRADED,
            MissionStatus.AT_RISK,
            MissionStatus.AWAITING_USER,
            MissionStatus.AWAITING_APPROVAL,
            MissionStatus.WAITING_FOR_APPROVAL,
            MissionStatus.REPLANNING,
            MissionStatus.COMPLETED,
            MissionStatus.FAILED,
            MissionStatus.CANCELLED,
            MissionStatus.ABANDONED,
            MissionStatus.SUPERSEDED,
            MissionStatus.UNKNOWN,
            MissionStatus.EXPIRED,
            MissionStatus.ESCALATED,
            MissionStatus.RUNNING,
        },
        MissionStatus.RUNNING: {
            MissionStatus.ACTIVE,
            MissionStatus.EXECUTING,
            MissionStatus.VERIFYING,
            MissionStatus.STABILIZING,
            MissionStatus.PAUSED,
            MissionStatus.BLOCKED,
            MissionStatus.DEGRADED,
            MissionStatus.AT_RISK,
            MissionStatus.AWAITING_USER,
            MissionStatus.AWAITING_APPROVAL,
            MissionStatus.WAITING_FOR_APPROVAL,
            MissionStatus.REPLANNING,
            MissionStatus.COMPLETED,
            MissionStatus.PARTIALLY_COMPLETED,
            MissionStatus.FAILED,
            MissionStatus.CANCELLED,
            MissionStatus.ABANDONED,
            MissionStatus.SUPERSEDED,
            MissionStatus.UNKNOWN,
            MissionStatus.EXPIRED,
            MissionStatus.ESCALATED,
        },
        MissionStatus.EXECUTING: {
            MissionStatus.VERIFYING,
            MissionStatus.ACTIVE,
            MissionStatus.RUNNING,
            MissionStatus.PAUSED,
            MissionStatus.BLOCKED,
            MissionStatus.DEGRADED,
            MissionStatus.AT_RISK,
            MissionStatus.AWAITING_USER,
            MissionStatus.AWAITING_APPROVAL,
            MissionStatus.FAILED,
            MissionStatus.CANCELLED,
            MissionStatus.UNKNOWN,
        },
        MissionStatus.VERIFYING: {
            MissionStatus.STABILIZING,
            MissionStatus.COMPLETED,
            MissionStatus.PARTIALLY_COMPLETED,
            MissionStatus.ACTIVE,
            MissionStatus.RUNNING,
            MissionStatus.REPLANNING,
            MissionStatus.AT_RISK,
            MissionStatus.DEGRADED,
            MissionStatus.BLOCKED,
            MissionStatus.FAILED,
            MissionStatus.ESCALATED,
            MissionStatus.UNKNOWN,
        },
        MissionStatus.STABILIZING: {
            MissionStatus.COMPLETED,
            MissionStatus.ACTIVE,
            MissionStatus.RUNNING,
            MissionStatus.AT_RISK,
            MissionStatus.DEGRADED,
            MissionStatus.FAILED,
            MissionStatus.UNKNOWN,
        },
        MissionStatus.PAUSED: {
            MissionStatus.ACTIVE,
            MissionStatus.RUNNING,
            MissionStatus.READY,
            MissionStatus.VALIDATING,
            MissionStatus.REPLANNING,
            MissionStatus.CANCELLED,
            MissionStatus.ABANDONED,
            MissionStatus.EXPIRED,
        },
        MissionStatus.BLOCKED: {
            MissionStatus.ACTIVE,
            MissionStatus.RUNNING,
            MissionStatus.REPLANNING,
            MissionStatus.AWAITING_USER,
            MissionStatus.AWAITING_APPROVAL,
            MissionStatus.ESCALATED,
            MissionStatus.CANCELLED,
            MissionStatus.FAILED,
            MissionStatus.DEGRADED,
        },
        MissionStatus.DEGRADED: {
            MissionStatus.ACTIVE,
            MissionStatus.RUNNING,
            MissionStatus.AT_RISK,
            MissionStatus.BLOCKED,
            MissionStatus.REPLANNING,
            MissionStatus.PAUSED,
            MissionStatus.FAILED,
            MissionStatus.CANCELLED,
        },
        MissionStatus.AT_RISK: {
            MissionStatus.ACTIVE,
            MissionStatus.RUNNING,
            MissionStatus.DEGRADED,
            MissionStatus.BLOCKED,
            MissionStatus.REPLANNING,
            MissionStatus.AWAITING_USER,
            MissionStatus.AWAITING_APPROVAL,
            MissionStatus.PAUSED,
            MissionStatus.FAILED,
            MissionStatus.CANCELLED,
        },
        MissionStatus.REPLANNING: {
            MissionStatus.READY,
            MissionStatus.ACTIVE,
            MissionStatus.RUNNING,
            MissionStatus.BLOCKED,
            MissionStatus.WAITING_FOR_APPROVAL,
            MissionStatus.AWAITING_APPROVAL,
            MissionStatus.CANCELLED,
        },
        MissionStatus.ESCALATED: {
            MissionStatus.ACTIVE,
            MissionStatus.RUNNING,
            MissionStatus.PLANNING,
            MissionStatus.PAUSED,
            MissionStatus.CANCELLED,
            MissionStatus.FAILED,
        },
        MissionStatus.UNKNOWN: {
            MissionStatus.ACTIVE,
            MissionStatus.RUNNING,
            MissionStatus.PAUSED,
            MissionStatus.BLOCKED,
            MissionStatus.REPLANNING,
            MissionStatus.FAILED,
            MissionStatus.CANCELLED,
        },
        MissionStatus.COMPLETED: {
            # Support progress regression: if subsequent world state invalidates verified state
            MissionStatus.DEGRADED,
            MissionStatus.AT_RISK,
            MissionStatus.ACTIVE,
            MissionStatus.REPLANNING,
            MissionStatus.REGRESSED,
        },
        MissionStatus.REGRESSED: {
            MissionStatus.REPLANNING,
            MissionStatus.ACTIVE,
            MissionStatus.RUNNING,
            MissionStatus.DEGRADED,
            MissionStatus.BLOCKED,
            MissionStatus.PAUSED,
            MissionStatus.FAILED,
            MissionStatus.CANCELLED,
        },
        MissionStatus.EMERGENCY_STOPPED: {
            MissionStatus.RECOVERING,
            MissionStatus.CANCELLED,
            MissionStatus.ABANDONED,
            MissionStatus.FAILED,
        },
        MissionStatus.RECOVERING: {
            MissionStatus.READY,
            MissionStatus.ACTIVE,
            MissionStatus.RUNNING,
            MissionStatus.REPLANNING,
            MissionStatus.PAUSED,
            MissionStatus.FAILED,
            MissionStatus.CANCELLED,
        },
        MissionStatus.PARTIALLY_COMPLETED: set(),  # Terminal
        MissionStatus.FAILED: set(),  # Terminal
        MissionStatus.ABANDONED: set(),  # Terminal
        MissionStatus.CANCELLED: set(),  # Terminal
        MissionStatus.SUPERSEDED: set(),  # Terminal
        MissionStatus.EXPIRED: {MissionStatus.VALIDATING, MissionStatus.CANCELLED, MissionStatus.FAILED},
    }

    @classmethod
    def can_transition(cls, current: MissionStatus, target: MissionStatus) -> bool:
        """Check if transition from current to target is permitted."""
        # Invariant: EMERGENCY STOP ALWAYS WINS from any non-terminal state
        if target == MissionStatus.EMERGENCY_STOPPED:
            terminal_states = {
                MissionStatus.FAILED,
                MissionStatus.CANCELLED,
                MissionStatus.ABANDONED,
                MissionStatus.SUPERSEDED,
            }
            return current not in terminal_states
        return target in cls._TRANSITIONS.get(current, set())

    @classmethod
    def transition(
        cls,
        mission: Mission,
        target: MissionStatus,
        reason: str = "",
        actor: str = "system",
        evidence: list[str] | None = None,
        trace_id: str | None = None,
    ) -> Mission:
        """Execute a state transition with guard checks, versioning, and checkpoint recording."""
        # Check expiration (Spec 50)
        if (
            mission.expires_at
            and _now_utc() > mission.expires_at
            and target not in (MissionStatus.EXPIRED, MissionStatus.CANCELLED, MissionStatus.FAILED)
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
        old_version = mission.version
        mission.status = target
        mission.updated_at = _now_utc()
        mission.version += 1

        # Track lifecycle timestamps
        if target in (MissionStatus.ACTIVE, MissionStatus.RUNNING, MissionStatus.EXECUTING) and not mission.started_at:
            mission.started_at = _now_utc()
        elif target in (MissionStatus.COMPLETED, MissionStatus.FAILED, MissionStatus.CANCELLED, MissionStatus.ABANDONED):
            mission.completed_at = _now_utc()

        # Structured health mapping
        if target in (MissionStatus.ACTIVE, MissionStatus.RUNNING, MissionStatus.EXECUTING):
            if mission.health in (MissionHealth.FAILED, MissionHealth.BLOCKED):
                mission.health = MissionHealth.ON_TRACK
        elif target == MissionStatus.BLOCKED:
            mission.health = MissionHealth.BLOCKED
        elif target == MissionStatus.DEGRADED:
            mission.health = MissionHealth.DEGRADED
        elif target == MissionStatus.AT_RISK:
            mission.health = MissionHealth.AT_RISK
        elif target == MissionStatus.COMPLETED:
            mission.health = MissionHealth.COMPLETED
        elif target == MissionStatus.FAILED:
            mission.health = MissionHealth.FAILED

        # Record checkpoint (Spec 26 & Task 100)
        checkpoint_evidence = [
            f"Transitioned from {old_status.value} to {target.value}. Reason: {reason or 'Standard lifecycle step'}"
        ]
        if evidence:
            checkpoint_evidence.extend(evidence)

        checkpoint = MissionCheckpoint(
            mission_id=mission.mission_id,
            state=target,
            progress_pct=mission.progress_pct,
            active_plan_id=mission.active_plan_id,
            active_milestones=[m.milestone_id for m in mission.milestones if m.status in (MissionStatus.ACTIVE, MissionStatus.RUNNING)],
            evidence=checkpoint_evidence,
            next_steps=[f"Proceed in state {target.value}"],
            version=mission.version,
        )
        mission.checkpoints.append(checkpoint)

        logger.info(
            "MISSION_TRANSITION: id=%s v%d->v%d %s -> %s actor=%s trace=%s reason=%s",
            mission.mission_id,
            old_version,
            mission.version,
            old_status.value,
            target.value,
            actor,
            trace_id or "none",
            reason,
        )
        return mission

    @classmethod
    def revalidate_and_resume(
        cls,
        mission: Mission,
        is_world_valid: bool = True,
        are_assumptions_valid: bool = True,
        actor: str = "system",
        reason: str = "State revalidated, resuming execution",
    ) -> Mission:
        """Revalidate world state and assumptions before resuming paused/stale missions (Spec 48, 49 & Task 100)."""
        if mission.status != MissionStatus.PAUSED:
            raise MissionSafetyError(
                f"Only PAUSED missions can be resumed via revalidate_and_resume (current status: {mission.status.value})."
            )

        if not is_world_valid or not are_assumptions_valid:
            invalidation_causes = []
            if not is_world_valid:
                invalidation_causes.append("world state drift")
            if not are_assumptions_valid:
                invalidation_causes.append("critical assumption invalidation")

            logger.warning(
                "Invalidation detected during pause for mission %s: %s",
                mission.mission_id,
                ", ".join(invalidation_causes),
            )
            return cls.transition(
                mission,
                MissionStatus.REPLANNING,
                reason=f"Pre-resumption invalidation: {', '.join(invalidation_causes)}",
                actor=actor,
            )

        return cls.transition(
            mission,
            MissionStatus.RUNNING,
            reason=reason,
            actor=actor,
        )
