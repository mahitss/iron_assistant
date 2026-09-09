"""Agent Checkpointing, Failure Recovery, Handoffs, and Human Escalation (Task 44)."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from app.agents.contracts import AgentContract

logger = logging.getLogger("kairo.agents.recovery")


def utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass
class AgentCheckpoint:
    """State checkpoint capturing intermediate progress for long-running agents (Spec 110, 111)."""

    checkpoint_id: str
    contract_id: str
    agent_id: str
    progress_percentage: int
    saved_state: dict[str, Any]
    evidence_refs: list[str]
    artifact_ids: list[str]
    created_at: datetime = field(default_factory=utc_now)


@dataclass
class AgentHandoff:
    """Authorized handoff transfer of a task between agents (Spec 112, 113)."""

    handoff_id: str
    contract_id: str
    source_agent_id: str
    target_agent_id: str
    reason: str
    state_payload: dict[str, Any]
    is_authorized: bool = False
    created_at: datetime = field(default_factory=utc_now)


class AgentRecoveryManager:
    """Coordinates checkpointing, task resumption, authorized handoffs, and human escalation."""

    def __init__(self) -> None:
        self._checkpoints: dict[str, AgentCheckpoint] = {}  # checkpoint_id -> AgentCheckpoint
        self._handoffs: dict[str, AgentHandoff] = {}        # handoff_id -> AgentHandoff

    def save_checkpoint(
        self,
        contract: AgentContract,
        progress_percentage: int,
        state_data: dict[str, Any],
        evidence_refs: list[str] | None = None,
        artifact_ids: list[str] | None = None,
    ) -> AgentCheckpoint:
        """Checkpoint progress during long-running tasks (Spec 110)."""
        chk = AgentCheckpoint(
            checkpoint_id=f"chk_{uuid.uuid4().hex[:10]}",
            contract_id=contract.contract_id,
            agent_id=contract.agent_id,
            progress_percentage=progress_percentage,
            saved_state=dict(state_data),
            evidence_refs=evidence_refs or [],
            artifact_ids=artifact_ids or [],
        )
        self._checkpoints[chk.checkpoint_id] = chk
        logger.info("Saved agent checkpoint '%s' for contract '%s'", chk.checkpoint_id, contract.contract_id)
        return chk

    def initiate_handoff(
        self,
        contract: AgentContract,
        target_agent_id: str,
        reason: str,
        state_payload: dict[str, Any],
        target_capabilities: list[str],
        required_capability: str,
    ) -> AgentHandoff:
        """Transfer task to another agent with capability and authorization validation (Spec 112, 113)."""
        # Validate target capability
        is_capable = required_capability.lower() in [c.lower() for c in target_capabilities]
        if not is_capable:
            logger.warning("Handoff rejected: Target agent '%s' lacks capability '%s'", target_agent_id, required_capability)

        handoff = AgentHandoff(
            handoff_id=f"hnd_{uuid.uuid4().hex[:10]}",
            contract_id=contract.contract_id,
            source_agent_id=contract.agent_id,
            target_agent_id=target_agent_id,
            reason=reason,
            state_payload=state_payload,
            is_authorized=is_capable,
        )

        if is_capable:
            # Reassign contract
            contract.agent_id = target_agent_id
            logger.info("Authorized task handoff from '%s' to '%s'", handoff.source_agent_id, target_agent_id)

        self._handoffs[handoff.handoff_id] = handoff
        return handoff

    def should_escalate_to_human(
        self,
        repeated_failures: int,
        has_critical_disagreement: bool,
        is_missing_authorization: bool,
    ) -> tuple[bool, str]:
        """Determine whether situation requires escalating to a human operator (Spec 115, 116)."""
        if is_missing_authorization:
            return True, "Escalation: Required action exceeds contract permission and requires explicit human approval."
        if has_critical_disagreement:
            return True, "Escalation: Irreconcilable disagreement between specialists requires human judgment."
        if repeated_failures >= 3:
            return True, f"Escalation: Specialist subtask failed {repeated_failures} consecutive times."
        return False, "Autonomous resolution within normal operating bounds."
