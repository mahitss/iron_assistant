"""Master Autonomous Execution Governance & Action Transaction Coordinator (Task 95).

Coordinates:
- The authoritative boundary between deliberate decisions and low-level ToolExecutor execution
- 22-state rigid transaction lifecycle
- 18-gate pre-flight validation
- Execution dispatch, empirical observation capture, post-condition verification
- Stability window evaluations
- Saga compensation & rollback orchestration
- Decision memory & reliability feedback loops
- EmergencyStop fail-closed enforcement
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
import hashlib
import json
import logging
import threading
from typing import Any
import uuid

from sqlalchemy.orm import Session

from app.decision.domain import DecisionLifecycleState, DecisionOutcomeRecord, VerificationStatus
from app.decision.intelligence_service import DecisionIntelligenceService, get_decision_intelligence_service
from app.events.bus import get_event_bus
from app.events.schemas import Event
from app.execution.db_models import ActionTransactionModel
from app.execution.domain import (
    ActionObservation,
    ActionTransaction,
    OutcomeType,
    PostCondition,
    SagaStep,
    TargetBinding,
    TargetType,
    TransactionStatus,
    VerificationState,
    _now_utc,
    _uuid_hex,
)
from app.execution.preflight import PreflightValidationEngine
from app.execution.verification import ExecutionVerificationEngine
from app.security.emergency_stop import EmergencyStopService, get_emergency_stop_service
from app.security.exceptions import EmergencyStopActiveError
from app.tools.executor import ToolExecutor
from app.tools.registry import get_tool_registry
from app.tools.schemas import ToolCall, ToolResult

logger = logging.getLogger("kairo.execution.service")


class ExecutionGovernanceService:
    """Master production-grade service for Kairo Action Transactions and Execution Governance."""

    def __init__(
        self,
        emergency_stop: EmergencyStopService | None = None,
        tool_executor: ToolExecutor | None = None,
        decision_service: DecisionIntelligenceService | None = None,
        db: Session | None = None,
    ) -> None:
        self.emergency_stop = emergency_stop or get_emergency_stop_service()
        self.db = db
        self._lock = threading.RLock()

        self.decision_service = decision_service or get_decision_intelligence_service()
        self.preflight_engine = PreflightValidationEngine(decision_service=self.decision_service)
        self.verification_engine = ExecutionVerificationEngine()

        if tool_executor:
            self.tool_executor = tool_executor
        else:
            self.tool_executor = ToolExecutor(registry=get_tool_registry())

        # In-memory transaction and idempotency cache
        self._transactions: dict[str, ActionTransaction] = {}
        self._idempotency_map: dict[str, str] = {}  # idempotency_key -> transaction_id

    def _emit_event(self, event_type: str, details: dict[str, Any]) -> None:
        """Publish canonical event to Kairo nervous system."""
        try:
            bus = get_event_bus()
            ev = Event(
                event_type=event_type,
                source="execution_governance",
                payload=details,
            )
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(bus.publish(ev))
            except RuntimeError:
                pass
        except Exception as ex:
            logger.debug("Event publish skipped: %s", ex)

    def _verify_emergency_stop(self, user_id: str | None = None) -> None:
        """Fail-closed immediately if EmergencyStop is active."""
        if self.emergency_stop.is_stopped(user_id):
            raise EmergencyStopActiveError("Emergency stop is ACTIVE. Action execution is blocked.")

    # --------------------------------------------------------------------------
    # 1. Action Preparation & Idempotency (Phases 1, 8, 10, 11)
    # --------------------------------------------------------------------------

    async def prepare_transaction(
        self,
        decision_id: str,
        capability_id: str,
        action_reference: str,
        parameters: dict[str, Any],
        target: TargetBinding,
        user_id: str = "default_user",
        capability_version: str = "1.0.0",
        idempotency_key: str | None = None,
        postconditions: list[PostCondition] | None = None,
        stability_window_seconds: float = 0.0,
        compensation_action: str | None = None,
        timeout_seconds: float = 30.0,
    ) -> ActionTransaction:
        """Create or retrieve an idempotent ActionTransaction bound to explicit target."""
        self._verify_emergency_stop(user_id)

        # 1. Compute stable idempotency key if not provided
        if not idempotency_key:
            norm_params = json.dumps(parameters, sort_keys=True)
            raw = f"{decision_id}:{capability_id}:{action_reference}:{target.target_id}:{norm_params}"
            idempotency_key = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]

        with self._lock:
            # 2. Check duplicate idempotency (Phase 8)
            existing_tx_id = self._idempotency_map.get(idempotency_key)
            if existing_tx_id and existing_tx_id in self._transactions:
                logger.info("Returning existing transaction '%s' for idempotency key", existing_tx_id)
                return self._transactions[existing_tx_id]

            # 3. Verify originating decision currency (Phase 25)
            dec = self.decision_service.get_decision(decision_id)
            if not dec:
                raise ValueError(f"Originating decision '{decision_id}' does not exist.")

            now = _now_utc()
            tx_id = f"txn_{uuid.uuid4().hex[:12]}"

            txn = ActionTransaction(
                transaction_id=tx_id,
                decision_id=decision_id,
                task_id=dec.task_id,
                capability_id=capability_id,
                capability_version=capability_version,
                action_reference=action_reference,
                status=TransactionStatus.CREATED,
                idempotency_key=idempotency_key,
                target=target,
                parameters=parameters,
                timeout_seconds=timeout_seconds,
                start_deadline=now + timedelta(minutes=10),
                transaction_deadline=now + timedelta(minutes=30),
                postconditions=postconditions or [],
                stability_window_seconds=stability_window_seconds,
                compensation_action=compensation_action,
                user_id=user_id,
            )

            self._transactions[tx_id] = txn
            self._idempotency_map[idempotency_key] = tx_id

            if self.db is not None:
                self._persist_transaction(txn)

            self._emit_event("action.created", {"transaction_id": tx_id, "decision_id": decision_id})

            # Transition CREATED -> PREPARING
            txn.transition_to(TransactionStatus.PREPARING)
            return txn

    # --------------------------------------------------------------------------
    # 2. Pre-Flight Validation (Phase 3)
    # --------------------------------------------------------------------------

    async def run_preflight(
        self,
        transaction_id: str,
        db_session: Any = None,
    ) -> tuple[bool, ActionTransaction]:
        """Execute the complete 18-gate pre-flight validation matrix."""
        self._verify_emergency_stop()

        with self._lock:
            txn = self._transactions.get(transaction_id)
            if not txn:
                raise KeyError(f"Transaction '{transaction_id}' not found.")

            txn.transition_to(TransactionStatus.PREFLIGHT)
            self._emit_event("action.preflight_started", {"transaction_id": transaction_id})

        # Run 18 pre-flight gates
        dec = self.decision_service.get_decision(txn.decision_id)
        passed, results = await self.preflight_engine.validate_transaction(
            transaction=txn,
            decision=dec,
            db_session=db_session,
        )

        with self._lock:
            txn.preflight_checks = results

            if not passed:
                txn.transition_to(TransactionStatus.BLOCKED, reason="Pre-flight validation failed")
                self._emit_event("action.preflight_failed", {"transaction_id": transaction_id})
                self._emit_event("action.blocked", {"transaction_id": transaction_id, "reason": "Pre-flight failure"})
                return False, txn

            self._emit_event("action.preflight_passed", {"transaction_id": transaction_id})

            # Check if approval is mandated
            if dec and dec.status == DecisionLifecycleState.AWAITING_APPROVAL and not txn.approval_reference:
                txn.transition_to(TransactionStatus.AWAITING_APPROVAL)
                self._emit_event("action.awaiting_approval", {"transaction_id": transaction_id})
                return False, txn

            # Advance lifecycle: AUTHORIZED -> ALLOCATED -> READY
            txn.transition_to(TransactionStatus.AUTHORIZED)
            self._emit_event("action.authorization_verified", {"transaction_id": transaction_id})

            txn.transition_to(TransactionStatus.ALLOCATED)
            self._emit_event("action.resources_allocated", {"transaction_id": transaction_id})

            txn.transition_to(TransactionStatus.READY)
            self._emit_event("action.ready", {"transaction_id": transaction_id})

            if self.db is not None:
                self._persist_transaction(txn)

            return True, txn

    # --------------------------------------------------------------------------
    # 3. Execution, Observation & Verification (Phases 9, 15, 17, 18, 19)
    # --------------------------------------------------------------------------

    async def execute_transaction(
        self,
        transaction_id: str,
        approval_id: str | None = None,
        db_session: Any = None,
    ) -> ActionTransaction:
        """Execute authorized action, capture observations, and verify post-conditions."""
        self._verify_emergency_stop()

        with self._lock:
            txn = self._transactions.get(transaction_id)
            if not txn:
                raise KeyError(f"Transaction '{transaction_id}' not found.")

            if approval_id:
                txn.approval_reference = approval_id

            # If not in READY state, attempt preflight
            if txn.status in (TransactionStatus.CREATED, TransactionStatus.PREPARING, TransactionStatus.PREFLIGHT):
                passed, _ = await self.run_preflight(transaction_id, db_session=db_session)
                if not passed:
                    return txn

            if txn.status == TransactionStatus.AWAITING_APPROVAL:
                if not approval_id:
                    raise PermissionError(f"Transaction '{transaction_id}' requires approval_id to proceed.")
                txn.transition_to(TransactionStatus.AUTHORIZED)
                txn.transition_to(TransactionStatus.ALLOCATED)
                txn.transition_to(TransactionStatus.READY)

            if txn.status != TransactionStatus.READY:
                raise ValueError(f"Cannot execute transaction in state '{txn.status}'.")

            txn.transition_to(TransactionStatus.EXECUTING)
            self._emit_event("action.execution_started", {"transaction_id": transaction_id})

        # 1. Dispatch through ToolExecutor (Phase 9)
        tool_name = txn.action_reference.replace("tool:", "")
        tool_call = ToolCall(
            name=tool_name,
            arguments=txn.parameters,
            id=transaction_id,
        )

        tool_result: ToolResult | None = None
        exec_error: Exception | None = None

        try:
            tool_result = await asyncio.wait_for(
                self.tool_executor.execute(
                    tool_call=tool_call,
                    user_id=txn.user_id,
                    session_id=transaction_id,
                    approval_id=txn.approval_reference,
                    correlation_id=txn.correlation_id,
                    db_session=db_session,
                ),
                timeout=txn.timeout_seconds,
            )
        except asyncio.TimeoutError:
            logger.error("Transaction '%s' execution timed out after %s seconds", transaction_id, txn.timeout_seconds)
            with self._lock:
                txn.transition_to(TransactionStatus.UNKNOWN, reason="Execution timed out; outcome indeterminate")
                self._emit_event("action.execution_failed", {"transaction_id": transaction_id, "reason": "Timeout"})
                self._emit_event("action.outcome_unknown", {"transaction_id": transaction_id})
                return txn
        except Exception as ex:
            exec_error = ex
            logger.error("Transaction '%s' execution crashed: %s", transaction_id, ex)

        with self._lock:
            # 2. Capture Observation (Phase 15)
            obs = await self.verification_engine.capture_observation(
                transaction=txn,
                tool_result=tool_result,
                raw_output=str(exec_error) if exec_error else "",
                exit_code=1 if exec_error else 0,
            )
            self._emit_event("action.observation_recorded", {"transaction_id": transaction_id, "obs_id": obs.observation_id})

            if exec_error or (tool_result and not tool_result.success):
                txn.transition_to(TransactionStatus.FAILED, reason=str(exec_error or tool_result.error))
                self._emit_event("action.execution_failed", {"transaction_id": transaction_id})

                # Check if compensation is configured (Phase 20)
                if txn.compensation_action:
                    asyncio.create_task(self.rollback_transaction(transaction_id, reason="Post-failure auto rollback"))
                return txn

            # 3. Transition to OBSERVING -> VERIFYING (Phase 17)
            txn.transition_to(TransactionStatus.OBSERVING)
            txn.transition_to(TransactionStatus.VERIFYING)
            self._emit_event("action.verification_started", {"transaction_id": transaction_id})

        # 4. Perform Post-Condition Verification & Stability Window Check (Phase 17 & 18)
        ver_state, outcome, summary = await self.verification_engine.verify_transaction(
            transaction=txn,
            tool_result=tool_result,
        )

        with self._lock:
            if ver_state == VerificationState.PASSED:
                txn.transition_to(TransactionStatus.SUCCEEDED)
                self._emit_event("action.verification_passed", {"transaction_id": transaction_id})
                self._emit_event("action.execution_completed", {"transaction_id": transaction_id})
                self._emit_event("action.outcome_confirmed", {"transaction_id": transaction_id})
            elif ver_state == VerificationState.PARTIAL:
                txn.transition_to(TransactionStatus.SUCCEEDED)
                self._emit_event("action.partial_success", {"transaction_id": transaction_id})
            elif ver_state == VerificationState.UNKNOWN:
                txn.transition_to(TransactionStatus.UNKNOWN)
                self._emit_event("action.verification_unknown", {"transaction_id": transaction_id})
                self._emit_event("action.outcome_unknown", {"transaction_id": transaction_id})
            else:
                txn.transition_to(TransactionStatus.FAILED)
                self._emit_event("action.verification_failed", {"transaction_id": transaction_id})

            # 5. Feedback to Decision Intelligence (Phase 25)
            self._record_decision_outcome(txn, outcome)

            if self.db is not None:
                self._persist_transaction(txn)

            return txn

    def _record_decision_outcome(self, txn: ActionTransaction, outcome: OutcomeType) -> None:
        """Record verified outcome back to Task 94 Decision Intelligence."""
        try:
            out_rec = DecisionOutcomeRecord(
                decision_id=txn.decision_id,
                predicted_outcome=txn.parameters,
                actual_outcome=txn.outcome_summary,
                deviation_score=txn.deviation_score,
                regret_score=txn.regret_score,
                verification_status=VerificationStatus.VERIFIED if outcome == OutcomeType.FULL_SUCCESS else VerificationStatus.FAILED,
                lessons_learned=[f"Transaction {txn.transaction_id} achieved {outcome.value}"],
            )
            self.decision_service.record_outcome(out_rec)
        except Exception as ex:
            logger.debug("Outcome feedback to Decision Intelligence skipped: %s", ex)

    # --------------------------------------------------------------------------
    # 4. Cancellation & Emergency Stop (Phases 13 & 14)
    # --------------------------------------------------------------------------

    async def cancel_transaction(self, transaction_id: str, reason: str = "Cancelled by user") -> ActionTransaction:
        """Cancel a pending, pre-flighted, or running transaction."""
        with self._lock:
            txn = self._transactions.get(transaction_id)
            if not txn:
                raise KeyError(f"Transaction '{transaction_id}' not found.")

            txn.transition_to(TransactionStatus.CANCELLED, reason=reason)
            self._emit_event("action.execution_cancelled", {"transaction_id": transaction_id, "reason": reason})

            if self.db is not None:
                self._persist_transaction(txn)

            return txn

    # --------------------------------------------------------------------------
    # 5. Rollback & Compensation (Phase 20)
    # --------------------------------------------------------------------------

    async def rollback_transaction(self, transaction_id: str, reason: str = "Rollback initiated") -> ActionTransaction:
        """Execute authorized rollback compensation."""
        self._verify_emergency_stop()

        with self._lock:
            txn = self._transactions.get(transaction_id)
            if not txn:
                raise KeyError(f"Transaction '{transaction_id}' not found.")

            if txn.status == TransactionStatus.ROLLED_BACK:
                return txn

            if not txn.can_transition_to(TransactionStatus.ROLLING_BACK):
                raise ValueError(f"Cannot rollback transaction in state '{txn.status}'.")

            txn.transition_to(TransactionStatus.ROLLING_BACK, reason=reason)
            self._emit_event("action.rollback_started", {"transaction_id": transaction_id, "reason": reason})

        # If a compensation action is registered, execute it through ToolExecutor
        if txn.compensation_action:
            tool_name = txn.compensation_action.replace("tool:", "")
            tool_call = ToolCall(name=tool_name, arguments=txn.parameters, id=f"rb_{transaction_id}")
            try:
                await self.tool_executor.execute(tool_call=tool_call, user_id=txn.user_id)
            except Exception as ex:
                logger.error("Rollback execution error: %s", ex)

        with self._lock:
            txn.transition_to(TransactionStatus.ROLLED_BACK)
            txn.rollback_reference = f"rb_{transaction_id}"
            self._emit_event("action.rollback_completed", {"transaction_id": transaction_id})

            if self.db is not None:
                self._persist_transaction(txn)

            return txn

    # --------------------------------------------------------------------------
    # 6. Crash State Reconciliation (Phase 22 & 37)
    # --------------------------------------------------------------------------

    async def reconcile_transaction(self, transaction_id: str) -> ActionTransaction:
        """Inspect empirical state for UNKNOWN transactions to confirm outcome."""
        with self._lock:
            txn = self._transactions.get(transaction_id)
            if not txn:
                raise KeyError(f"Transaction '{transaction_id}' not found.")

            if txn.status != TransactionStatus.UNKNOWN:
                return txn

            txn.transition_to(TransactionStatus.RECOVERING)
            self._emit_event("action.recovery_started", {"transaction_id": transaction_id})

        # Re-probe post-conditions
        ver_state, outcome, _ = await self.verification_engine.verify_transaction(txn)

        with self._lock:
            if ver_state == VerificationState.PASSED:
                txn.transition_to(TransactionStatus.RECOVERED)
                txn.outcome_type = OutcomeType.FULL_SUCCESS
                self._emit_event("action.recovery_completed", {"transaction_id": transaction_id, "result": "RECOVERED"})
            else:
                txn.transition_to(TransactionStatus.FAILED)
                txn.outcome_type = OutcomeType.FAILED
                self._emit_event("action.recovery_completed", {"transaction_id": transaction_id, "result": "FAILED"})

            if self.db is not None:
                self._persist_transaction(txn)

            return txn

    # --------------------------------------------------------------------------
    # 7. Persistence & Read Queries
    # --------------------------------------------------------------------------

    def _persist_transaction(self, txn: ActionTransaction) -> None:
        """Persist transaction state to relational database."""
        try:
            db_model = self.db.query(ActionTransactionModel).filter_by(transaction_id=txn.transaction_id).first()
            if not db_model:
                db_model = ActionTransactionModel(
                    transaction_id=txn.transaction_id,
                    decision_id=txn.decision_id,
                    task_id=txn.task_id,
                    workflow_id=txn.workflow_id,
                    capability_id=txn.capability_id,
                    capability_version=txn.capability_version,
                    action_reference=txn.action_reference,
                    status=txn.status.value,
                    idempotency_key=txn.idempotency_key,
                    target_json=txn.target.model_dump(),
                    parameters_json=txn.parameters,
                    authorization_reference=txn.authorization_reference,
                    approval_reference=txn.approval_reference,
                    governance_reference=txn.governance_reference,
                    resource_reference=txn.resource_reference,
                    preflight_checks_json=[p.model_dump() for p in txn.preflight_checks],
                    observations_json=[o.model_dump(mode="json") for o in txn.observations],
                    postconditions_json=[c.model_dump() for c in txn.postconditions],
                    verification_state=txn.verification_state.value,
                    outcome_type=txn.outcome_type.value if txn.outcome_type else None,
                    outcome_summary_json=txn.outcome_summary,
                    deviation_score=txn.deviation_score,
                    regret_score=txn.regret_score,
                    user_id=txn.user_id,
                    correlation_id=txn.correlation_id,
                    trace_id=txn.trace_id,
                    created_at=txn.created_at,
                    started_at=txn.started_at,
                    completed_at=txn.completed_at,
                )
                self.db.add(db_model)
            else:
                db_model.status = txn.status.value
                db_model.verification_state = txn.verification_state.value
                db_model.outcome_type = txn.outcome_type.value if txn.outcome_type else None
                db_model.outcome_summary_json = txn.outcome_summary
                db_model.preflight_checks_json = [p.model_dump() for p in txn.preflight_checks]
                db_model.observations_json = [o.model_dump(mode="json") for o in txn.observations]
                db_model.postconditions_json = [c.model_dump() for c in txn.postconditions]
                db_model.started_at = txn.started_at
                db_model.completed_at = txn.completed_at

            self.db.commit()
        except Exception as ex:
            logger.warning("Failed to persist ActionTransaction to DB: %s", ex)
            self.db.rollback()

    def list_transactions(self, limit: int = 50) -> list[ActionTransaction]:
        with self._lock:
            txns = list(self._transactions.values())
            txns.sort(key=lambda t: t.created_at, reverse=True)
            return txns[:limit]

    def get_transaction(self, transaction_id: str) -> ActionTransaction | None:
        with self._lock:
            return self._transactions.get(transaction_id)


# Process-wide singleton
_global_execution_service: ExecutionGovernanceService | None = None


def get_execution_governance_service(db: Session | None = None) -> ExecutionGovernanceService:
    """Retrieve or create the process-wide ExecutionGovernanceService singleton."""
    global _global_execution_service
    if _global_execution_service is None:
        _global_execution_service = ExecutionGovernanceService(db=db)
    elif db is not None and _global_execution_service.db is None:
        _global_execution_service.db = db
    return _global_execution_service
