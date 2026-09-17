"""Event Trigger Coalescer for Kairo Control Plane (Task 102).

Prevents event storms and runaway loop multiplication by coalescing compatible
triggers within a bounded window into a single cohesive ControlCycle.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.control_plane.domain import ControlCycle, CyclePriority, TriggerType, _now_utc, _uuid_hex

logger = logging.getLogger("kairo.control_plane.coalescer")

TRIGGER_PRIORITY_MAP: Dict[TriggerType, CyclePriority] = {
    TriggerType.RECOVERY_EVENT: CyclePriority.EMERGENCY,
    TriggerType.ACTION_FAILURE: CyclePriority.CRITICAL,
    TriggerType.RISK_ESCALATION: CyclePriority.CRITICAL,
    TriggerType.SITUATION_ESCALATION: CyclePriority.HIGH,
    TriggerType.USER_REQUEST: CyclePriority.HIGH,
    TriggerType.NEW_SITUATION: CyclePriority.HIGH,
    TriggerType.MISSION_CHANGE: CyclePriority.NORMAL,
    TriggerType.GOAL_CHANGE: CyclePriority.NORMAL,
    TriggerType.WORLD_STATE_DRIFT: CyclePriority.NORMAL,
    TriggerType.RELIABILITY_DEGRADATION: CyclePriority.NORMAL,
    TriggerType.CAPABILITY_CHANGE: CyclePriority.NORMAL,
    TriggerType.DEPENDENCY_CHANGE: CyclePriority.NORMAL,
    TriggerType.RESOURCE_CHANGE: CyclePriority.NORMAL,
    TriggerType.APPROVAL_RECEIVED: CyclePriority.HIGH,
    TriggerType.APPROVAL_REJECTED: CyclePriority.HIGH,
    TriggerType.AGENT_RESULT: CyclePriority.NORMAL,
    TriggerType.SCHEDULED_REVIEW: CyclePriority.LOW,
    TriggerType.SELF_MODEL_CHANGE: CyclePriority.NORMAL,
}


class ControlTriggerCoalescer:
    """Coalesces incoming trigger bursts into bounded ControlCycle candidates."""

    @classmethod
    def coalesce(
        cls,
        triggers: List[Dict[str, Any]],
        scope: str = "SYSTEM",
    ) -> ControlCycle:
        """Merges multiple concurrent triggers into a single prioritized ControlCycle."""
        if not triggers:
            return ControlCycle(
                trigger_type=TriggerType.SCHEDULED_REVIEW,
                priority=CyclePriority.LOW,
                scope=scope,
            )

        # 1. Determine highest priority trigger
        best_priority = CyclePriority.LOW
        primary_trigger = triggers[0]

        for trig in triggers:
            t_type = trig.get("trigger_type", TriggerType.USER_REQUEST)
            if isinstance(t_type, str):
                try:
                    t_type = TriggerType(t_type)
                except ValueError:
                    t_type = TriggerType.USER_REQUEST

            p = TRIGGER_PRIORITY_MAP.get(t_type, CyclePriority.NORMAL)
            if p.value < best_priority.value:
                best_priority = p
                primary_trigger = trig

        prim_type = primary_trigger.get("trigger_type", TriggerType.USER_REQUEST)
        if isinstance(prim_type, str):
            try:
                prim_type = TriggerType(prim_type)
            except ValueError:
                prim_type = TriggerType.USER_REQUEST

        cycle_id = _uuid_hex("cycle")
        now_str = _now_utc()

        logger.info(
            "Coalesced %d trigger events into ControlCycle %s with priority %s (Primary: %s)",
            len(triggers),
            cycle_id,
            best_priority.name,
            prim_type.value,
        )

        return ControlCycle(
            cycle_id=cycle_id,
            started_at=now_str,
            priority=best_priority,
            trigger_type=prim_type,
            trigger_payload=primary_trigger.get("payload", {}),
            coalesced_triggers=list(triggers),
            scope=scope,
            mission_ref=primary_trigger.get("mission_id"),
            situation_ref=primary_trigger.get("situation_id"),
        )
