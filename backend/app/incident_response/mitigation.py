"""Mitigation, containment, and blast radius reduction (Task 61)."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from app.incident_response.schemas import (
    ActionState,
    IncidentActionItem,
    ResponderRole,
    ResponseOptionItem,
)

logger = logging.getLogger(__name__)


class MitigationEngine:
    """Coordinates containment, traffic shedding, and immediate blast radius reduction.

    Invariant 33-35: Mitigation aims to stabilize and limit impact; it is distinct from full recovery.
    Invariant 113-115: Prepares authorized action specs for execution through ToolExecutor; no direct tool invocation.
    """

    def prepare_mitigation_action(
        self,
        incident_id: str,
        option: ResponseOptionItem,
        actor: str,
        parameters: dict[str, Any] | None = None,
    ) -> IncidentActionItem:
        """Create a structured, validated mitigation action item."""
        if not option.is_capability_available:
            raise ValueError(f"Cannot mitigate using option '{option.option_id}': capability unavailable.")

        action = IncidentActionItem(
            action_id=f"act_mit_{uuid.uuid4().hex[:8]}",
            incident_id=incident_id,
            action_type=f"MITIGATION_{option.strategy_type.upper()}",
            title=f"Mitigation: {option.title}",
            status=ActionState.PROPOSED if option.requires_approval else ActionState.AUTHORIZED,
            is_reversible=option.is_reversible,
            is_idempotent=True,
            requires_approval=option.requires_approval,
            executor_role=ResponderRole.OPERATOR,
            parameters=parameters or {"target_strategy": option.strategy_type},
            verification_spec={
                "metric_check": "error_rate_decrease",
                "threshold": "drop_below_1_percent",
                "timeout_seconds": 60,
            },
        )

        logger.info(
            "MITIGATION_ACTION_PREPARED: id=%s incident=%s requires_approval=%s",
            action.action_id,
            incident_id,
            action.requires_approval,
        )
        return action


mitigation_engine = MitigationEngine()
