"""Master Autonomous Reliability, Fault Analysis & Self-Healing Service for Kairo (Task 88)."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import logging
import time
from typing import Any, Dict, List, Optional, Set

from app.reliability.blast_radius import BlastRadiusAnalyzer
from app.reliability.correlator import RootCauseCorrelator
from app.reliability.detector import FailureDetector
from app.reliability.fault_injection import FaultInjectionEngine
from app.reliability.learning import ReliabilityLearner
from app.reliability.models import (
    FailureLifecycleState,
    FailureRecord,
    IncidentLifecycleState,
    IncidentRecord,
    RecoveryEvidenceRecord,
    RecoveryExecutionRecord,
    RecoveryStrategy,
    RecoveryStrategyType,
    SafeRecoveryClass,
    VerificationResult,
    VerificationState,
    generate_id,
)
from app.reliability.recovery_engine import RecoveryEngine
from app.reliability.subsystems import SubsystemRecoveryAdapter
from app.reliability.taxonomy import FailureSeverity, FailureType
from app.reliability.verifier import RecoveryVerifier

logger = logging.getLogger("kairo.reliability.service")


class ReliabilityService:
    """Master orchestrator for runtime reliability, failure correlation, blast-radius analysis,

    bounded recovery, non-LLM verification, and post-incident learning.
    """

    def __init__(
        self,
        detector: Optional[FailureDetector] = None,
        correlator: Optional[RootCauseCorrelator] = None,
        blast_radius: Optional[BlastRadiusAnalyzer] = None,
        recovery_engine: Optional[RecoveryEngine] = None,
        subsystems: Optional[SubsystemRecoveryAdapter] = None,
        verifier: Optional[RecoveryVerifier] = None,
        learner: Optional[ReliabilityLearner] = None,
        fault_injector: Optional[FaultInjectionEngine] = None,
    ) -> None:
        self.detector = detector or FailureDetector()
        self.correlator = correlator or RootCauseCorrelator()
        self.blast_radius = blast_radius or BlastRadiusAnalyzer()
        self.recovery_engine = recovery_engine or RecoveryEngine()
        self.subsystems = subsystems or SubsystemRecoveryAdapter()
        self.verifier = verifier or RecoveryVerifier()
        self.learner = learner or ReliabilityLearner()
        self.fault_injector = fault_injector or FaultInjectionEngine(enabled=False)

        # In-memory primary stores
        self._failures: Dict[str, FailureRecord] = {}
        self._incidents: Dict[str, IncidentRecord] = {}
        self._recoveries: Dict[str, RecoveryExecutionRecord] = {}
        self._evidence: Dict[str, RecoveryEvidenceRecord] = {}

        # Degraded capabilities tracking: capability_name -> reason
        self._degraded_capabilities: Dict[str, str] = {}

    # ==========================================================================
    # 1. FAILURE DETECTION & INCIDENT CREATION
    # ==========================================================================

    async def ingest_failure(
        self,
        exc_or_error: Exception | str | dict[str, Any],
        component: str,
        operation: str = "unspecified",
        correlation_id: str | None = None,
        trace_id: str | None = None,
        causation_id: str | None = None,
        status_code: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> FailureRecord:
        """Ingests, classifies, deduplicates, correlates, and associates a failure with an incident."""
        # 1. Classify and fingerprint failure
        failure = self.detector.ingest_signal(
            exc_or_error=exc_or_error,
            component=component,
            operation=operation,
            correlation_id=correlation_id,
            trace_id=trace_id,
            causation_id=causation_id,
            status_code=status_code,
            metadata=metadata,
        )
        self._failures[failure.failure_id] = failure
        failure.transition_to(FailureLifecycleState.CLASSIFIED)

        await self._emit_audit("reliability.failure.detected", {
            "failure_id": failure.failure_id,
            "failure_type": failure.failure_type.value,
            "component": component,
            "severity": failure.severity.value,
            "correlation_id": failure.correlation_id,
        })

        # 2. Correlate with active failures for root cause
        active_failures = [
            f for f in self._failures.values()
            if f.state not in (FailureLifecycleState.RECOVERED, FailureLifecycleState.ABORTED)
        ]
        root_cause = self.correlator.correlate(failure, active_failures)
        failure.root_cause_candidate = root_cause
        failure.transition_to(FailureLifecycleState.CORRELATED)

        # 3. Associate with or create IncidentRecord
        incident = self._find_or_create_incident(failure, root_cause)
        if failure.failure_id not in incident.failures:
            incident.failures.append(failure.failure_id)
        incident.last_seen_at = failure.timestamp

        # 4. Blast-Radius Analysis
        failure.transition_to(FailureLifecycleState.ASSESSING)
        radius = await self.blast_radius.calculate_blast_radius(
            component=root_cause,
            failure_type=failure.failure_type,
            severity=failure.severity,
            metadata=failure.metadata,
        )
        incident.blast_radius_summary = radius
        incident.affected_components = list(set(incident.affected_components + radius.get("affected_subsystems", [])))

        await self._emit_audit("reliability.blast_radius.calculated", {
            "incident_id": incident.incident_id,
            "root_cause": root_cause,
            "impact_score": radius.get("systemic_impact_score", 0.0),
            "affected_subsystems": radius.get("affected_subsystems", []),
        })

        # 5. Check storm / crash loop conditions
        if self.detector.detect_storm(failure.fingerprint):
            await self._emit_audit("reliability.storm.detected", {
                "fingerprint": failure.fingerprint,
                "component": component,
                "threshold": self.detector.storm_threshold,
            })

        if self.detector.is_in_crash_loop(component):
            await self._emit_audit("reliability.crash_loop.detected", {
                "component": component,
                "action": "HALT_AUTOMATIC_RESTARTS",
            })

        return failure

    def _find_or_create_incident(self, failure: FailureRecord, root_cause: str) -> IncidentRecord:
        """Finds active incident matching root cause or creates a new one."""
        for inc in self._incidents.values():
            if inc.current_state in (IncidentLifecycleState.OPEN, IncidentLifecycleState.INVESTIGATING, IncidentLifecycleState.MONITORING):
                if inc.root_cause_candidate.lower() == root_cause.lower():
                    return inc

        # Create new incident
        inc = IncidentRecord(
            severity=failure.severity,
            root_cause_candidate=root_cause,
            affected_components=[failure.component],
            failure_fingerprint=failure.fingerprint,
        )
        self._incidents[inc.incident_id] = inc
        return inc

    # ==========================================================================
    # 2. RECOVERY EXECUTION & VERIFICATION
    # ==========================================================================

    async def execute_recovery_for_incident(
        self,
        incident_id: str,
        caller_identity: str = "system",
        dry_run: bool = False,
    ) -> RecoveryExecutionRecord:
        """Executes bounded, authorized, and resource-reserved recovery for an incident."""
        incident = self._incidents.get(incident_id)
        if not incident:
            raise ValueError(f"Incident {incident_id} not found")

        comp = incident.root_cause_candidate
        async with self.recovery_engine._get_lock(comp):
            # 1. Select Strategy
            is_crash_loop = self.detector.is_in_crash_loop(comp)
            # Find primary failure
            primary_fail: Optional[FailureRecord] = None
            if incident.failures:
                primary_fail = self._failures.get(incident.failures[0])

            if primary_fail is None:
                # Synthetic fallback failure record
                primary_fail = FailureRecord(
                    failure_type=FailureType.RUNTIME_FAILURE,
                    component=comp,
                    severity=incident.severity,
                    root_cause_candidate=comp,
                )

            strategy = self.recovery_engine.select_strategy(primary_fail, incident, is_crash_loop=is_crash_loop)
            if primary_fail.state == FailureLifecycleState.ASSESSING:
                primary_fail.transition_to(FailureLifecycleState.RECOVERY_SELECTED)

            # Create execution record
            attempt_no = self.recovery_engine._get_attempt_count(comp, strategy.strategy_type) + 1
            exec_rec = RecoveryExecutionRecord(
                failure_id=primary_fail.failure_id,
                incident_id=incident.incident_id,
                component=comp,
                strategy=strategy.strategy_type,
                risk_class=strategy.risk,
                attempt_number=attempt_no,
                is_dry_run=dry_run,
            )
            self._recoveries[exec_rec.recovery_id] = exec_rec
            incident.recovery_attempts.append(exec_rec.recovery_id)

            await self._emit_audit("reliability.recovery.selected", {
                "incident_id": incident.incident_id,
                "strategy": strategy.strategy_type.value,
                "component": comp,
                "attempt": attempt_no,
            })

            # Check cooldown
            in_cd, cd_rem = self.recovery_engine.is_in_cooldown(comp, strategy)
            if in_cd:
                exec_rec.state = FailureLifecycleState.ESCALATED
                exec_rec.error_message = f"Cooldown active ({cd_rem:.1f}s remaining)"
                return exec_rec

            # 2. Authorize Recovery
            if primary_fail.state == FailureLifecycleState.RECOVERY_SELECTED:
                primary_fail.transition_to(FailureLifecycleState.AUTHORIZING)

            auth_ok, decision_id, approval_id = await self.recovery_engine.authorize_recovery(
                strategy=strategy,
                component=comp,
                user_id=caller_identity,
            )
            exec_rec.authorization_decision_id = decision_id
            exec_rec.approval_id = approval_id

            if not auth_ok:
                if decision_id == "EMERGENCY_STOP_ACTIVE":
                    exec_rec.state = FailureLifecycleState.EMERGENCY_STOPPED
                    if primary_fail.state != FailureLifecycleState.EMERGENCY_STOPPED:
                        primary_fail.transition_to(FailureLifecycleState.EMERGENCY_STOPPED)
                else:
                    exec_rec.state = FailureLifecycleState.ESCALATED
                    if primary_fail.state != FailureLifecycleState.ESCALATED:
                        primary_fail.transition_to(FailureLifecycleState.ESCALATED)
                exec_rec.error_message = f"Authorization denied: {decision_id}"
                return exec_rec

            # 3. Dry-Run Preflight Return
            if dry_run:
                exec_rec.state = FailureLifecycleState.RECOVERED
                exec_rec.verification_state = VerificationState.VERIFIED_RECOVERED
                exec_rec.action_details = {"dry_run": True, "preflight": "valid"}
                return exec_rec

            # 4. Reserve Recovery Budget
            task_id = f"task_rec_{exec_rec.recovery_id}"
            budget_ok, rsv_id = await self.recovery_engine.reserve_recovery_budget(strategy, task_id)
            if not budget_ok:
                exec_rec.state = FailureLifecycleState.ESCALATED
                exec_rec.error_message = "RECOVERY_RESOURCE_BLOCKED: Insufficient cognitive/system budget"
                return exec_rec
            exec_rec.resource_reservation_id = rsv_id

            # 5. Execute Recovery Action
            exec_rec.state = FailureLifecycleState.RECOVERING
            if incident.current_state in (IncidentLifecycleState.OPEN, IncidentLifecycleState.INVESTIGATING):
                incident.transition_to(IncidentLifecycleState.RECOVERING)
            if primary_fail.state == FailureLifecycleState.AUTHORIZING:
                primary_fail.transition_to(FailureLifecycleState.RECOVERING)

            self.recovery_engine.record_attempt(comp, strategy.strategy_type)
            if strategy.strategy_type in (RecoveryStrategyType.RESTART_COMPONENT, RecoveryStrategyType.RESTART_PROCESS):
                self.detector.record_restart(comp)

            start_t = time.perf_counter()
            try:
                action_res = await self.subsystems.execute_recovery_action(
                    component=comp,
                    strategy=strategy.strategy_type,
                    parameters={"is_idempotent": strategy.side_effect_class == "SAFE_READ"},
                )
                exec_rec.action_details = action_res
            except Exception as exc:
                logger.error("Recovery execution exception on %s: %s", comp, exc)
                action_res = {"status": "FAILED", "error": str(exc)}
                exec_rec.error_message = str(exc)
            finally:
                # Release reserved recovery budget
                await self.recovery_engine.release_recovery_budget(rsv_id, task_id)

            duration = time.perf_counter() - start_t
            exec_rec.completed_at = datetime.now(timezone.utc)

            # 6. Verify Recovery
            if primary_fail.state == FailureLifecycleState.RECOVERING:
                primary_fail.transition_to(FailureLifecycleState.VERIFYING)

            v_result = await self.verifier.verify_recovery(
                component=comp,
                strategy=strategy.strategy_type,
                action_result=action_res,
            )
            exec_rec.verification_state = v_result.state
            exec_rec.verification_details = v_result.details

            # 7. Post-Recovery State & Stability Transition
            if v_result.state == VerificationState.VERIFIED_RECOVERED:
                exec_rec.state = FailureLifecycleState.RECOVERED
                if primary_fail.state == FailureLifecycleState.VERIFYING:
                    primary_fail.transition_to(FailureLifecycleState.RECOVERED)

                # Clear crash loop if verified clean
                self.detector.clear_crash_loop(comp)

                # Enter stability window
                self.verifier.initiate_stability_window(incident)

                await self._emit_audit("reliability.recovery.verified", {
                    "incident_id": incident.incident_id,
                    "recovery_id": exec_rec.recovery_id,
                    "component": comp,
                    "duration_seconds": round(duration, 3),
                })
            else:
                exec_rec.state = FailureLifecycleState.ESCALATED
                if primary_fail.state == FailureLifecycleState.VERIFYING:
                    primary_fail.transition_to(FailureLifecycleState.ESCALATED)

                await self._emit_audit("reliability.recovery.failed", {
                    "incident_id": incident.incident_id,
                    "recovery_id": exec_rec.recovery_id,
                    "component": comp,
                    "error": exec_rec.error_message,
                })

            # 8. Learning & Calibration
            self.learner.record_outcome(
                incident=incident,
                execution=exec_rec,
                actual_duration_seconds=duration,
                actual_cost={"cpu": strategy.resource_cost.get("cpu", 1.0)},
            )

            # Record Evidence Bundle
            evidence_rec = RecoveryEvidenceRecord(
                failure_id=primary_fail.failure_id,
                recovery_id=exec_rec.recovery_id,
                strategy=strategy.strategy_type.value,
                before_state={"status": primary_fail.severity.value, "error": primary_fail.message},
                action_taken=exec_rec.action_details,
                after_state={"verification": v_result.state.value},
                verification=v_result.details,
                resource_usage={"cost": strategy.resource_cost, "duration_s": duration},
                timestamps={"started": exec_rec.started_at.isoformat(), "completed": exec_rec.completed_at.isoformat()},
                result_status=exec_rec.state.value,
            )
            self._evidence[evidence_rec.evidence_id] = evidence_rec

            return exec_rec

    # ==========================================================================
    # 3. STABILITY MONITORING & MAINTENANCE
    # ==========================================================================

    def reconcile_stability_windows(self) -> List[str]:
        """Evaluates active incidents in MONITORING state; resolves stable incidents."""
        resolved: List[str] = []
        for inc in list(self._incidents.values()):
            if inc.current_state == IncidentLifecycleState.MONITORING:
                if self.verifier.evaluate_stability_window(inc):
                    resolved.append(inc.incident_id)
        return resolved

    # ==========================================================================
    # 4. HEALTH, INTROSPECTION & DIAGNOSTICS
    # ==========================================================================

    def get_health_status(self) -> Dict[str, Any]:
        """Returns consolidated health, incident counts, and crash loops."""
        open_incidents = [
            i for i in self._incidents.values()
            if i.current_state not in (IncidentLifecycleState.RESOLVED, IncidentLifecycleState.CLOSED)
        ]
        crash_loops = list(self.detector._crash_loops)

        status_str = "HEALTHY"
        if crash_loops or any(i.severity == FailureSeverity.P0 for i in open_incidents):
            status_str = "CRITICAL"
        elif any(i.severity == FailureSeverity.P1 for i in open_incidents):
            status_str = "DEGRADED"
        elif open_incidents:
            status_str = "RECOVERING"

        return {
            "status": status_str,
            "open_incidents_count": len(open_incidents),
            "total_failures_count": len(self._failures),
            "crash_loops_active": crash_loops,
            "degraded_capabilities": self._degraded_capabilities,
            "fault_injection_enabled": self.fault_injector.config.enabled,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def list_incidents(self) -> List[IncidentRecord]:
        return list(self._incidents.values())

    def get_incident(self, incident_id: str) -> Optional[IncidentRecord]:
        return self._incidents.get(incident_id)

    def list_failures(self) -> List[FailureRecord]:
        return list(self._failures.values())

    def get_failure(self, failure_id: str) -> Optional[FailureRecord]:
        return self._failures.get(failure_id)

    def list_recoveries(self) -> List[RecoveryExecutionRecord]:
        return list(self._recoveries.values())

    def get_recovery(self, recovery_id: str) -> Optional[RecoveryExecutionRecord]:
        return self._recoveries.get(recovery_id)

    def get_evidence(self, recovery_id: str) -> Optional[RecoveryEvidenceRecord]:
        for evi in self._evidence.values():
            if evi.recovery_id == recovery_id:
                return evi
        return None

    # ==========================================================================
    # 5. AUDIT EVENT DISPATCHING
    # ==========================================================================

    async def _emit_audit(self, event_type: str, payload: Dict[str, Any]) -> None:
        """Publishes audit and telemetry events through unified EventBus."""
        try:
            from app.events.bus import event_bus
            from app.events.schemas import Event, EventSeverity, ExecutionDomain
            ev = Event(
                event_type=event_type,
                severity=EventSeverity.INFO if "detected" not in event_type else EventSeverity.WARNING,
                execution_domain=ExecutionDomain.RUNTIME,
                payload=payload,
            )
            await event_bus.publish(ev)
        except Exception as e:
            logger.debug("EventBus dispatch notice for %s: %s", event_type, e)


# Global singleton instance
reliability_service = ReliabilityService()
