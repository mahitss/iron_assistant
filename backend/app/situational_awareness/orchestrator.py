"""Proactive Response Orchestrator for Task 99.

Coordinates the end-to-end operational pipeline:
Situation
    ↓ assess
    ↓ attention
    ↓ decision candidate (Decision Intelligence)
    ↓ ActionTransaction (Execution Governance)
    ↓ ToolExecutor / Rust Runtime
    ↓ Observation
    ↓ Verification (World-State Reconciliation)
    ↓ Situation Update / Resolution

Enforces:
- EXECUTION != VERIFIED STATE (Never resolve based solely on execution success)
- NO_ACTION is a first-class outcome with persisted rationale
- EmergencyStop blocks all proactive action execution fail-closed
- Proactive capabilities (CAN_OBSERVE, CAN_NOTIFY, CAN_INVESTIGATE, CAN_PROPOSE_ACTION, CAN_EXECUTE_ACTION)
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
import logging
from typing import Any, Dict, List, Optional, Set

from app.decision.domain import DecisionOption, DecisionType
from app.events.bus import get_event_bus
from app.events.schemas import Event
from app.execution.domain import TransactionStatus
from app.situational_awareness.bridges import SubsystemBridges, subsystem_bridges
from app.situational_awareness.domain import (
    ProactivePolicyCapability,
    SignalRecord,
    SituationInterventionRecord,
    SituationLifecycleState,
    SituationRecord,
    SituationSeverity,
    SituationTimelineEntry,
    generate_uuid,
    utc_now,
)
from app.situational_awareness.lifecycle import SituationLifecycleManager, situation_lifecycle_manager

logger = logging.getLogger("kairo.situational_awareness.orchestrator")


class ProactiveResponseOrchestrator:
    """Master orchestrator executing the proactive situation evaluation, intervention, and reality verification loop."""

    def __init__(
        self,
        bridges: Optional[SubsystemBridges] = None,
        lifecycle: Optional[SituationLifecycleManager] = None,
    ) -> None:
        self.bridges = bridges or subsystem_bridges
        self.lifecycle = lifecycle or situation_lifecycle_manager
        self._event_bus = get_event_bus()

    # =========================================================================
    # 1. POLICY-AWARE CAPABILITIES (Section 48)
    # =========================================================================

    def evaluate_proactive_capabilities(self, situation: SituationRecord) -> set[ProactivePolicyCapability]:
        """Determines proactive policy permissions for a situation without granting execution authorization."""
        capabilities: set[ProactivePolicyCapability] = {ProactivePolicyCapability.CAN_OBSERVE}

        # If Emergency Stop is active, observation is allowed for forensics, but intervention is halted
        if self.bridges.is_emergency_stopped(situation.user_id):
            return capabilities

        # Can notify if not suppressed
        if not self.lifecycle.is_suppressed(situation.situation_id):
            capabilities.add(ProactivePolicyCapability.CAN_NOTIFY)

        # Can investigate if confidence is moderate or uncertainty exists
        if situation.confidence < 0.95 or situation.uncertainty > 0.2:
            capabilities.add(ProactivePolicyCapability.CAN_INVESTIGATE)

        # Can propose action if actionable severity
        if situation.severity in (SituationSeverity.MEDIUM, SituationSeverity.HIGH, SituationSeverity.CRITICAL):
            capabilities.add(ProactivePolicyCapability.CAN_PROPOSE_ACTION)

        # Automatic execution without human approval is strictly limited to benign low-risk automated remediations
        if situation.severity == SituationSeverity.LOW and situation.confidence >= 0.95:
            capabilities.add(ProactivePolicyCapability.CAN_EXECUTE_ACTION)

        return capabilities

    # =========================================================================
    # 2. PROACTIVE ORCHESTRATION PIPELINE (Section 17, 18)
    # =========================================================================

    async def orchestrate_response(
        self,
        situation: SituationRecord,
        candidate_options: Optional[list[DecisionOption]] = None,
        expected_postconditions: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Executes the complete proactive response cycle from attention through verified reality reconciliation."""
        now = utc_now()
        report: dict[str, Any] = {
            "situation_id": situation.situation_id,
            "lifecycle_state": situation.lifecycle_state.value,
            "started_at": now.isoformat(),
            "proactive_pipeline_steps": [],
        }

        # STEP 1: Emergency Stop Check (Section 30)
        safe, reason = self.bridges.check_proactive_safety(situation)
        if not safe:
            report["status"] = "BLOCKED_BY_EMERGENCY_STOP"
            report["reason"] = reason
            situation.timeline.append(
                SituationTimelineEntry(
                    event_type="PROACTIVE_PIPELINE_HALTED",
                    summary=reason,
                    timestamp=now,
                )
            )
            return report

        # STEP 2: Attention Prioritization (Section 15)
        attention_priority = self.bridges.submit_to_attention_engine(situation)
        report["attention_priority"] = attention_priority
        p_str = f"{attention_priority:.2f}" if isinstance(attention_priority, (int, float)) else str(attention_priority)
        report["proactive_pipeline_steps"].append(f"Attention priority assigned: {p_str}")

        # STEP 3: Knowledge Graph Registration (Section 25)
        self.bridges.register_situation_in_knowledge_graph(situation)

        # STEP 4: First-Class NO_ACTION Check (Section 18)
        if situation.severity == SituationSeverity.INFO or self.lifecycle.is_suppressed(situation.situation_id):
            report["status"] = "NO_ACTION"
            report["rationale"] = "Severity is INFO or situation is actively suppressed under quiet policy."
            situation.timeline.append(
                SituationTimelineEntry(
                    event_type="NO_ACTION_DECIDED",
                    summary=report["rationale"],
                    timestamp=utc_now(),
                )
            )
            return report

        # STEP 5: Decision Intelligence Deliberation (Section 28)
        options = candidate_options or [
            DecisionOption(
                option_id="opt_restart_service",
                title="Restart service or capability",
                description="Perform controlled restart of affected entity",
                option_type=DecisionType.ACTION,
                expected_utility=0.85,
            ),
            DecisionOption(
                option_id="opt_no_action",
                title="No immediate intervention",
                description="Continue observing under threshold limits",
                option_type=DecisionType.NO_ACTION,
                expected_utility=0.40,
            ),
        ]

        dec_id, selected_option = self.bridges.evaluate_decision_candidate(situation, options)
        if not selected_option or selected_option.option_type == DecisionType.NO_ACTION:
            report["status"] = "NO_ACTION"
            report["decision_id"] = dec_id
            report["rationale"] = "Decision Intelligence selected NO_ACTION path as optimal trade-off."
            situation.timeline.append(
                SituationTimelineEntry(
                    event_type="NO_ACTION_DECIDED",
                    summary=report["rationale"],
                    timestamp=utc_now(),
                )
            )
            return report

        report["selected_option"] = selected_option.title
        report["proactive_pipeline_steps"].append(f"Decision Intelligence selected option: {selected_option.title}")

        # STEP 6: ActionTransaction Creation & Execution (Section 17, 29)
        target_entity = situation.affected_entities[0] if situation.affected_entities else "system"
        postconditions = expected_postconditions or {"status": "HEALTHY", "reconciled": True}

        self.lifecycle.transition(situation, SituationLifecycleState.INTERVENTION_PENDING, reason="ActionTransaction initiated")

        tx = await self.bridges.initiate_action_transaction(
            situation=situation,
            action_name=selected_option.title,
            target_entity_id=target_entity,
            expected_postconditions=postconditions,
            decision_id=dec_id,
        )

        if not tx:
            report["status"] = "INTERVENTION_FAILED_PREFLIGHT"
            return report

        self.lifecycle.transition(situation, SituationLifecycleState.INTERVENTION_ACTIVE, reason=f"Executing ActionTransaction {tx.transaction_id}")
        report["action_transaction_id"] = tx.transaction_id
        report["proactive_pipeline_steps"].append(f"ActionTransaction {tx.transaction_id} executed.")

        # Transition to OBSERVING
        self.lifecycle.transition(situation, SituationLifecycleState.OBSERVING, reason="Action complete; entering observation window for reality verification")

        # STEP 7: Post-Action Verification via World-State Reconciliation (Section 10)
        # CRITICAL: EXECUTION != VERIFIED STATE.
        verification_res = await self.bridges.verify_post_action_reality(situation, tx.transaction_id)
        report["world_state_verification"] = verification_res

        if verification_res.get("verified") is True:
            # Reality verified: Move from STABILIZING to RESOLVED
            self.lifecycle.transition(situation, SituationLifecycleState.STABILIZING, reason="Post-action state verified by telemetry")
            self.lifecycle.transition(situation, SituationLifecycleState.RESOLVED, reason="Situation verified resolved against empirical state")
            report["status"] = "RESOLVED_VERIFIED"
            report["proactive_pipeline_steps"].append("Situation empirically verified and RESOLVED.")
        else:
            # Postcondition mismatch: Must NOT falsely resolve!
            mismatches = verification_res.get("mismatches", {})
            report["status"] = "FAILED_POSTCONDITION_MISMATCH"
            report["mismatches"] = mismatches
            # Revert to ACTIVE or ESCALATING
            self.lifecycle.transition(
                situation,
                SituationLifecycleState.ACTIVE,
                reason=f"Action reported success but empirical postconditions failed: {mismatches}",
            )
            report["proactive_pipeline_steps"].append(
                f"EXECUTION != VERIFIED STATE: Postconditions failed verification ({mismatches}). Situation remains ACTIVE."
            )

        return report

    async def deliberate_and_respond(
        self,
        situation: SituationRecord,
        candidate_options: Optional[list[DecisionOption]] = None,
        expected_postconditions: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Deliberate candidate responses and orchestrate proactive response pipeline."""
        return await self.orchestrate_response(
            situation=situation,
            candidate_options=candidate_options,
            expected_postconditions=expected_postconditions,
        )


# Global orchestrator singleton
proactive_response_orchestrator = ProactiveResponseOrchestrator()
proactive_orchestrator = proactive_response_orchestrator
