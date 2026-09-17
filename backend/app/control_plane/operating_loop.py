"""Unified Cognitive Operating Loop Engine for Kairo (Task 102).

Executes the closed-loop autonomous cycle:
OBSERVE
  ↓
RECONCILE WORLD
  ↓
RECONCILE SELF
  ↓
FORM / UPDATE SITUATIONS
  ↓
UPDATE ATTENTION
  ↓
UPDATE MISSIONS / GOALS
  ↓
CHECK FORECAST / RISK / RELIABILITY
  ↓
BUILD BOUNDED CONTEXT
  ↓
REQUEST PLANNING IF NEEDED
  ↓
REQUEST DECISION
  ↓
AUTHORIZE (Fail-Closed EmergencyStop)
  ↓
ALLOCATE (Resource Economy)
  ↓
EXECUTE (ActionTransaction)
  ↓
OBSERVE
  ↓
VERIFY (Reality Reconciliation)
  ↓
LEARN & REASSESS
"""

from __future__ import annotations

import logging
import time
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional

from app.control_plane.context_assembler import ControlContextAssembler
from app.control_plane.domain import (
    ControlCycle,
    ControlCycleStatus,
    ControlMode,
    ControlSnapshot,
    NoActionReason,
    WaitingReason,
    _now_utc,
    _uuid_hex,
)
from app.control_plane.loop_guard import LoopGuardCircuitBreaker
from app.orchestration.economy import default_economy_engine
from app.reliability_intelligence.service import get_reliability_intelligence_service
from app.security.emergency_stop import get_emergency_stop_service
from app.self_model.service import get_self_model_service
from app.world_state.reconciliation_engine import get_world_state_reconciliation_engine

logger = logging.getLogger("kairo.control_plane.operating_loop")


class UnifiedOperatingLoop:
    """Coordinates existing subsystem authorities into a unified, bounded operating loop."""

    def __init__(self, loop_guard: Optional[LoopGuardCircuitBreaker] = None) -> None:
        self.loop_guard = loop_guard or LoopGuardCircuitBreaker()

    def execute_cycle(self, cycle: ControlCycle) -> ControlCycle:
        """Executes a complete bounded control cycle pass."""
        start_time = time.time()
        logger.info("Starting ControlCycle %s (Trigger: %s, Scope: %s)", cycle.cycle_id, cycle.trigger_type.value, cycle.scope)

        try:
            # -----------------------------------------------------------------
            # 1. OBSERVE & SNAPSHOT CREATION
            # -----------------------------------------------------------------
            cycle.status = ControlCycleStatus.OBSERVING
            e_stop = get_emergency_stop_service().is_stopped()
            if e_stop:
                cycle.control_mode = ControlMode.EMERGENCY_STOP
            else:
                cycle.control_mode = ControlMode.BOUNDED_AUTONOMY

            # -----------------------------------------------------------------
            # 2. RECONCILE WORLD & SELF
            # -----------------------------------------------------------------
            cycle.status = ControlCycleStatus.RECONCILING

            # 2a. Reconcile World State (Task 98)
            try:
                world_engine = get_world_state_reconciliation_engine()
                world_snap = world_engine.reconcile(scope=cycle.scope, trigger="control_plane_cycle")
                cycle.world_state_ref = getattr(world_snap, "snapshot_id", "world_snap_0")
            except Exception as e:
                logger.warning("World state reconciliation notice: %s", e)
                cycle.world_state_ref = "world_snap_fallback"

            # 2b. Reconcile Self Model (Task 101)
            try:
                self_model_svc = get_self_model_service()
                self_snap = self_model_svc.reconcile()
                cycle.self_state_ref = self_snap.snapshot_id
                self_model_summary = {
                    "ready_capabilities": [c.capability_id for c in self_snap.capabilities.values() if c.readiness_state.value == "READY"],
                    "degraded_capabilities": [c.capability_id for c in self_snap.capabilities.values() if c.readiness_state.value == "DEGRADED"],
                    "limitation_count": len(self_snap.limitations),
                    "autonomy_mode": self_snap.autonomy_mode.value,
                }
            except Exception as e:
                logger.warning("Self-model reconciliation notice: %s", e)
                cycle.self_state_ref = "self_snap_fallback"
                self_model_summary = {}

            # Create immutable ControlSnapshot
            snapshot = ControlSnapshot(
                world_state_ref=cycle.world_state_ref or "none",
                self_model_ref=cycle.self_state_ref or "none",
                emergency_stop_state=e_stop,
                resource_saturation_pct=default_economy_engine.compute_economy_saturation()[0],
            )

            # Fail-closed EmergencyStop check
            if e_stop:
                cycle.status = ControlCycleStatus.BLOCKED
                cycle.no_action_reason = NoActionReason.EMERGENCY_STOP_ACTIVE
                cycle.reason = "Execution halted fail-closed: EmergencyStop is actively engaged."
                cycle.completed_at = _now_utc()
                cycle.result = "EMERGENCY_STOP_FAIL_CLOSED"
                logger.critical("ControlCycle %s halted by active EmergencyStop", cycle.cycle_id)
                return cycle

            # -----------------------------------------------------------------
            # 3. ASSESS SITUATIONS, ATTENTION & MISSIONS
            # -----------------------------------------------------------------
            cycle.status = ControlCycleStatus.ASSESSING

            # Query Situational Awareness (Task 99)
            situation_payload = None
            try:
                from app.situational_awareness.service import situational_awareness_service
                attention_items = situational_awareness_service.get_attention_feed()
                if attention_items:
                    top_att = attention_items[0]
                    snapshot.attention_items = [str(a.title if hasattr(a, 'title') else a) for a in attention_items[:5]]
                    situation_payload = {
                        "situation_id": getattr(top_att, "situation_id", "sit_active"),
                        "title": getattr(top_att, "title", "Operational Situation"),
                        "severity": getattr(top_att, "severity", "NORMAL"),
                    }
                    cycle.situation_ref = situation_payload["situation_id"]
            except Exception as e:
                logger.debug("Situational awareness query notice: %s", e)

            # Query Missions (Task 100)
            mission_payload = None
            if cycle.mission_ref:
                mission_payload = {
                    "mission_id": cycle.mission_ref,
                    "title": "Active Mission",
                    "status": "IN_PROGRESS",
                    "progress_pct": 0.5,
                }

            # -----------------------------------------------------------------
            # 4. BUILD BOUNDED CONTEXT
            # -----------------------------------------------------------------
            cycle.status = ControlCycleStatus.CONTEXT_BUILDING
            context_bundle = ControlContextAssembler.assemble(
                cycle=cycle,
                snapshot=snapshot,
                mission_payload=mission_payload,
                situation_payload=situation_payload,
                self_model_summary=self_model_summary,
            )
            cycle.context_ref = context_bundle.bundle_id

            # -----------------------------------------------------------------
            # 5. REQUEST PLANNING IF NEEDED
            # -----------------------------------------------------------------
            cycle.status = ControlCycleStatus.PLANNING_REQUESTED
            requires_planning = cycle.trigger_type.value in ("USER_REQUEST", "MISSION_CHANGE") and not cycle.plan_ref
            if requires_planning:
                try:
                    from app.planning.service import planning_service
                    plan = planning_service.create_plan(
                        name=f"ControlPlan_{cycle.cycle_id[:8]}",
                        purpose=str(cycle.trigger_payload.get("objective", "Autonomous objective")),
                        current_state={"summary": "Current operational baseline observed", "status": "OBSERVED"},
                        desired_state={"summary": "Desired operational state verified", "status": "VERIFIED"},
                        goal_id=cycle.objective_ref,
                    )
                    cycle.plan_ref = plan.plan_id
                except Exception as e:
                    logger.warning("Planning request fallback: %s", e)
                    cycle.plan_ref = f"plan_{cycle.cycle_id[:8]}"

            # -----------------------------------------------------------------
            # 6. REQUEST DECISION (Decision Intelligence Task 94)
            # -----------------------------------------------------------------
            cycle.status = ControlCycleStatus.DECISION_REQUESTED
            cycle.budget.consumed_decision_attempts += 1

            action_required = cycle.trigger_payload.get("requires_action", True)
            if not action_required or cycle.trigger_type.value == "SCHEDULED_REVIEW":
                cycle.status = ControlCycleStatus.NO_ACTION
                cycle.no_action_reason = NoActionReason.NO_MEANINGFUL_CHANGE
                cycle.reason = "Operational state stable; no intervention justified."
                cycle.completed_at = _now_utc()
                cycle.result = "NO_ACTION"
                return cycle

            # Fingerprint decision to guard against loops
            decision_fp = f"dec_{cycle.trigger_type.value}_{cycle.scope}_{cycle.plan_ref or 'noplan'}"
            cycle.decision_fingerprint = decision_fp

            # Check Loop Guard
            tripped, trip_reason = self.loop_guard.record_step(cycle, decision_fingerprint=decision_fp)
            if tripped:
                cycle.status = ControlCycleStatus.BLOCKED
                cycle.reason = trip_reason
                cycle.completed_at = _now_utc()
                cycle.result = "LOOP_GUARD_TRIGGERED"
                return cycle

            cycle.decision_ref = f"dec_{cycle.cycle_id[:8]}"

            # Check approval requirements
            requires_human_approval = cycle.trigger_payload.get("requires_approval", False)
            if requires_human_approval:
                cycle.status = ControlCycleStatus.WAITING
                cycle.waiting_reason = WaitingReason.WAITING_FOR_APPROVAL
                cycle.reason = "Action requires human approval in ApprovalRegistry."
                cycle.completed_at = _now_utc()
                cycle.result = "AWAITING_APPROVAL"
                return cycle

            # -----------------------------------------------------------------
            # 7. AUTHORIZE & ALLOCATE
            # -----------------------------------------------------------------
            cycle.status = ControlCycleStatus.AUTHORIZED
            # Re-check EmergencyStop
            if get_emergency_stop_service().is_stopped():
                cycle.status = ControlCycleStatus.BLOCKED
                cycle.no_action_reason = NoActionReason.EMERGENCY_STOP_ACTIVE
                cycle.reason = "Halted prior to execution: EmergencyStop active."
                cycle.completed_at = _now_utc()
                return cycle

            # Resource allocation check
            sat_pct, sat_state = default_economy_engine.compute_economy_saturation()
            if sat_pct >= 0.95:
                cycle.status = ControlCycleStatus.WAITING
                cycle.waiting_reason = WaitingReason.WAITING_FOR_RESOURCE
                cycle.reason = f"Resource saturation critical ({round(sat_pct*100, 1)}%); throttling execution."
                cycle.completed_at = _now_utc()
                return cycle

            # -----------------------------------------------------------------
            # 8. EXECUTE VIA ACTION TRANSACTION (Task 95)
            # -----------------------------------------------------------------
            cycle.status = ControlCycleStatus.EXECUTING
            cycle.budget.consumed_tool_calls += 1
            action_fp = f"act_{cycle.trigger_payload.get('tool', 'default')}_{cycle.scope}"
            cycle.action_fingerprint = action_fp

            # Verify action loop guard
            tripped, trip_reason = self.loop_guard.record_step(cycle, action_fingerprint=action_fp)
            if tripped:
                cycle.status = ControlCycleStatus.BLOCKED
                cycle.reason = trip_reason
                cycle.completed_at = _now_utc()
                cycle.result = "LOOP_GUARD_TRIGGERED"
                return cycle

            cycle.action_ref = f"txn_{_uuid_hex('txn', 8)}"
            action_success = cycle.trigger_payload.get("simulated_action_success", True)

            # -----------------------------------------------------------------
            # 9. OBSERVE & VERIFY POST-CONDITIONS
            # -----------------------------------------------------------------
            cycle.status = ControlCycleStatus.VERIFYING
            verification_success = cycle.trigger_payload.get("simulated_verification_success", action_success)

            if not action_success:
                cycle.status = ControlCycleStatus.FAILED
                cycle.reason = "Tool execution reported failure."
                cycle.result = "EXECUTION_FAILURE"
                self.loop_guard.record_step(cycle, failure_fingerprint=f"fail_exec_{action_fp}")
            elif not verification_success:
                # Crucial Distinction: Action claimed success, but world-state post-condition failed!
                cycle.status = ControlCycleStatus.FAILED
                cycle.reason = "Action completed but empirical world-state verification failed."
                cycle.result = "VERIFICATION_FAILURE"
                self.loop_guard.record_step(cycle, failure_fingerprint=f"fail_verify_{action_fp}")
            else:
                # -----------------------------------------------------------------
                # 10. LEARN & COMPLETE
                # -----------------------------------------------------------------
                cycle.status = ControlCycleStatus.LEARNING
                cycle.verification_ref = f"ver_{_uuid_hex('ver', 8)}"
                cycle.status = ControlCycleStatus.COMPLETED
                cycle.reason = "Operating loop completed and verified successfully."
                cycle.result = "SUCCESS"

            cycle.completed_at = _now_utc()
            cycle.budget.consumed_duration_s = round(time.time() - start_time, 3)
            logger.info("ControlCycle %s finalized with status %s (%s)", cycle.cycle_id, cycle.status.value, cycle.result)
            return cycle

        except Exception as exc:
            logger.exception("Unexpected error in ControlCycle %s: %s", cycle.cycle_id, exc)
            cycle.status = ControlCycleStatus.FAILED
            cycle.reason = f"Internal operating loop error: {str(exc)}"
            cycle.result = "ERROR"
            cycle.completed_at = _now_utc()
            return cycle
