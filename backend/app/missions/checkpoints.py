"""Durable Mission Checkpoints, Crash Recovery & Zero-Hidden-State Handoff Engine (Task 100)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from app.missions.schemas import (
    MilestoneStatus,
    Mission,
    MissionCheckpoint,
    MissionStatus,
)

logger = logging.getLogger("kairo.missions.checkpoints")


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class MissionCheckpointEngine:
    """Creates durable, reproducible checkpoints and coordinates crash recovery and handoffs."""

    @classmethod
    def create_checkpoint(
        cls,
        mission: Mission,
        label: str = "",
        context_summary: str = "",
        generate_handoff_manifest: bool = False,
        world_state_ref: dict[str, Any] | None = None,
        evidence: list[str] | None = None,
        risks: list[str] | None = None,
    ) -> MissionCheckpoint:
        """Capture an immutable, reproducible checkpoint and optionally attach a handoff manifest."""
        summary = context_summary or label
        cp = cls.create_durable_checkpoint(
            mission=mission,
            context_summary=summary,
            world_state_ref=world_state_ref,
            evidence=evidence,
            risks=risks,
        )
        if generate_handoff_manifest:
            cp.handoff_manifest = cls.generate_handoff_manifest(mission)
        return cp

    @classmethod
    def create_durable_checkpoint(
        cls,
        mission: Mission,
        context_summary: str = "",
        world_state_ref: dict[str, Any] | None = None,
        evidence: list[str] | None = None,
        risks: list[str] | None = None,
    ) -> MissionCheckpoint:
        """Capture an immutable, reproducible checkpoint of mission state."""
        active_ms = [m.milestone_id for m in mission.milestones if m.status in (MilestoneStatus.ACTIVE, MilestoneStatus.READY)]
        assumptions_snap = [
            {
                "assumption_id": a.assumption_id,
                "statement": a.statement,
                "status": a.status.value,
                "confidence": a.confidence,
            }
            for a in mission.assumptions
        ]

        checkpoint = MissionCheckpoint(
            mission_id=mission.mission_id,
            state=mission.status,
            progress_pct=mission.progress_pct,
            active_plan_id=mission.active_plan_id,
            active_milestones=active_ms,
            assumptions_snapshot=assumptions_snap,
            world_state_ref=world_state_ref or {},
            evidence=evidence or [f"Durable checkpoint created at state {mission.status.value}"],
            risks=risks or [],
            next_steps=[f"Resume progression from milestone {active_ms[0]}" if active_ms else "Evaluate ready milestones"],
            context_summary=context_summary or f"Mission '{mission.title}' in state {mission.status.value} with {mission.progress_pct}% progress.",
            timestamp=_now_utc(),
            version=mission.version,
        )

        mission.checkpoints.append(checkpoint)
        mission.updated_at = _now_utc()

        logger.info("CHECKPOINT_CREATED: mission=%s chk=%s v=%d state=%s", mission.mission_id, checkpoint.checkpoint_id, checkpoint.version, checkpoint.state.value)
        return checkpoint

    @classmethod
    def generate_handoff_manifest(cls, mission: Mission) -> dict[str, Any]:
        """Produce a zero-hidden-state manifest enabling safe transfer to another session/agent.

        Invariant: The new executor should reconstruct full mission context with zero missing state.
        """
        active_milestones = [
            {
                "milestone_id": m.milestone_id,
                "title": m.title,
                "status": m.status.value,
                "progress_pct": m.progress_pct,
                "blocked_reason": m.blocked_reason,
            }
            for m in mission.milestones
            if m.status in (MilestoneStatus.ACTIVE, MilestoneStatus.READY, MilestoneStatus.BLOCKED, MilestoneStatus.AT_RISK)
        ]

        assumptions_summary = [
            {"id": a.assumption_id, "statement": a.statement, "status": a.status.value, "confidence": a.confidence}
            for a in mission.assumptions
        ]

        blockers_summary = [
            {"id": b.blocker_id, "type": b.blocker_type, "description": b.description, "severity": b.severity.value}
            for b in mission.blockers
        ]

        latest_checkpoint = mission.checkpoints[-1].model_dump() if mission.checkpoints else None

        return {
            "mission_id": mission.mission_id,
            "title": mission.title,
            "objective": mission.objective or mission.description,
            "scope": mission.scope,
            "authority_scope": mission.authority_scope.value,
            "autonomy_level": mission.autonomy_level.value,
            "status": mission.status.value,
            "health": mission.health.value,
            "progress_pct": mission.progress_pct,
            "active_plan_id": mission.active_plan_id,
            "active_milestones": active_milestones,
            "completed_milestones": [m.milestone_id for m in mission.milestones if m.status == MilestoneStatus.COMPLETED],
            "active_assumptions": assumptions_summary,
            "assumptions": assumptions_summary,
            "blockers": blockers_summary,
            "active_situations": list(mission.active_situations),
            "active_decisions": list(mission.active_decisions),
            "active_actions": list(mission.active_actions),
            "deadline": mission.deadline.isoformat() if mission.deadline else None,
            "latest_checkpoint": latest_checkpoint,
            "version": mission.version,
            "handoff_timestamp": _now_utc().isoformat(),
        }

    @classmethod
    def recover_from_crash(
        cls,
        mission: Mission,
        reconciled_world_state: dict[str, Any] | None = None,
    ) -> tuple[Mission, str]:
        """Restore mission state after system crash or restart without duplicate action execution."""
        if not mission.checkpoints:
            return mission, "No checkpoints available; maintaining current persisted state"

        latest = mission.checkpoints[-1]

        # Invariant: Reconcile active execution against actual world state. Never blindly restart actions.
        in_flight_reset_count = 0
        for m in mission.milestones:
            if m.status in (MilestoneStatus.ACTIVE, MilestoneStatus.VERIFYING):
                # If world state proves completion, keep completed; otherwise reset to READY for re-verification
                if reconciled_world_state and reconciled_world_state.get(m.milestone_id, {}).get("completed"):
                    m.status = MilestoneStatus.COMPLETED
                    m.progress_pct = 100.0
                else:
                    m.status = MilestoneStatus.READY
                    m.blocked_reason = "Recovered from restart; re-verification required"
                    in_flight_reset_count += 1

        if mission.status == MissionStatus.EXECUTING:
            mission.status = MissionStatus.ACTIVE

        mission.version += 1
        mission.updated_at = _now_utc()

        msg = f"Recovered from checkpoint {latest.checkpoint_id} (version {latest.version}). Reset {in_flight_reset_count} in-flight milestones to READY."
        logger.info("MISSION_CRASH_RECOVERY: %s", msg)
        return mission, msg
