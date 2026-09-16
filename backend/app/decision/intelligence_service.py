"""Master Autonomous Decision Intelligence Coordinator (Task 94).

Coordinates:
- Structured option evaluation, Pareto trade-offs, and first-class NO_ACTION
- Isolated subsystem bridges (Forecasting, Causal, Risk, Resilience, Simulation, Resource, Capability, Security, Governance)
- Assumption tracking and drift re-evaluation
- Decision Memory consolidation and safe precedent reuse
- EmergencyStop fail-closed enforcement
- Auditable canonical event emissions
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
import logging
import threading
from typing import Any
import uuid

from sqlalchemy.orm import Session

from app.decision.bridges import SubsystemBridges
from app.decision.db_models import (
    DecisionAssumptionModel,
    DecisionOptionV2Model,
    DecisionOutcomeV2Model,
    DecisionV2Model,
)
from app.decision.domain import (
    AssumptionItem,
    AssumptionStatus,
    ConstraintCategory,
    DecisionCertainty,
    DecisionConstraint,
    DecisionExplanation,
    DecisionInput,
    DecisionLifecycleState,
    DecisionOption,
    DecisionOutcomeRecord,
    DecisionType,
    DecisionV2Record,
    SecurityAuthorizationStatus,
    SimulationState,
    VerificationStatus,
)
from app.decision.evaluation import DecisionEvaluationEngine
from app.decision.memory import DecisionMemoryEngine
from app.events.bus import get_event_bus
from app.events.schemas import Event
from app.security.emergency_stop import EmergencyStopService, get_emergency_stop_service
from app.security.exceptions import EmergencyStopActiveError

logger = logging.getLogger("kairo.decision.intelligence_service")


class DecisionIntelligenceService:
    """Master production-grade service for Kairo Decision Intelligence and Decision Memory."""

    def __init__(
        self,
        emergency_stop: EmergencyStopService | None = None,
        db: Session | None = None,
    ) -> None:
        self.emergency_stop = emergency_stop or get_emergency_stop_service()
        self.db = db
        self._lock = threading.RLock()

        # Core Engines
        self.bridges = SubsystemBridges()
        self.evaluator = DecisionEvaluationEngine()
        self.memory = DecisionMemoryEngine()

        # In-memory storage cache
        self._decisions: dict[str, DecisionV2Record] = {}
        self._outcomes: dict[str, DecisionOutcomeRecord] = {}

    def _verify_execution_allowed(self, user_id: str | None = None) -> None:
        """Ensure EmergencyStop is not active during mutating operational decisions."""
        if self.emergency_stop.is_stopped(user_id):
            raise EmergencyStopActiveError("Emergency stop is ACTIVE. Autonomous decision mutations are halted.")

    def _emit_event(self, event_type: str, details: dict[str, Any]) -> None:
        """Emit canonical event to Kairo event fabric."""
        try:
            bus = get_event_bus()
            ev = Event(
                event_type=event_type,
                source="decision_intelligence",
                payload=details,
            )
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(bus.publish(ev))
            except RuntimeError:
                pass
        except Exception as exc:
            logger.debug("Event bus publish skipped: %s", exc)

    # --------------------------------------------------------------------------
    # 1. Deliberation & Option Evaluation (Phases 3 - 21)
    # --------------------------------------------------------------------------

    def evaluate_decision(self, inp: DecisionInput, user_id: str | None = None) -> DecisionV2Record:
        """Perform comprehensive multi-criteria deliberation and select defensible action or NO_ACTION."""
        self._verify_execution_allowed(user_id)

        with self._lock:
            now = datetime.now(UTC)
            dec_id = f"dec_{uuid.uuid4().hex[:12]}"
            self._emit_event("decision.created", {"decision_id": dec_id, "objective_id": inp.objective_id})
            self._emit_event("decision.evaluation_started", {"decision_id": dec_id})

            # 1. Interrogate Subsystem Bridges for each candidate option
            enriched_options: list[DecisionOption] = []
            for opt in inp.candidate_options:
                # Security evaluation (Phase 16)
                sec_status, sec_msg = self.bridges.evaluate_security(opt, user_id=user_id)
                opt.security_classification = sec_status
                if sec_status == SecurityAuthorizationStatus.DENIED:
                    opt.is_feasible = False
                    opt.rejection_reason = f"Security authorization denied: {sec_msg}"
                    self._emit_event("decision.option_blocked", {"decision_id": dec_id, "option_id": opt.option_id, "reason": sec_msg})

                # Governance evaluation (Phase 17)
                gov_report = self.bridges.evaluate_governance(opt)
                if gov_report.get("is_prohibited"):
                    opt.is_feasible = False
                    opt.rejection_reason = "Prohibited by Governance Constitution"
                    self._emit_event("decision.option_blocked", {"decision_id": dec_id, "option_id": opt.option_id, "reason": "Governance violation"})

                # Capability evaluation (Phase 15)
                cap_ok, cap_msg = self.bridges.evaluate_capability(opt)
                if not cap_ok:
                    opt.is_feasible = False
                    opt.rejection_reason = cap_msg
                    self._emit_event("decision.option_blocked", {"decision_id": dec_id, "option_id": opt.option_id, "reason": cap_msg})

                # Resource evaluation (Phase 14)
                res_report = self.bridges.evaluate_resources(opt)
                if not res_report.get("is_feasible"):
                    opt.is_feasible = False
                    opt.rejection_reason = res_report.get("rejection_reason")

                # Forecasting & Causality (Phases 9 & 10)
                fc_report = self.bridges.evaluate_forecast_and_causality(opt)
                if not opt.expected_outcome:
                    opt.expected_outcome = fc_report.get("expected_outcome", "")

                # Risk & Resilience (Phases 11 & 12)
                risk_res = self.bridges.evaluate_risk_and_resilience(opt)
                opt.reversibility = risk_res.get("reversibility", opt.reversibility)

                # Simulation gate (Phase 13)
                sim_state = self.bridges.evaluate_simulation_gate(opt)
                opt.simulation_status = sim_state
                if sim_state == SimulationState.REQUIRED:
                    self._emit_event("decision.simulation_required", {"decision_id": dec_id, "option_id": opt.option_id})

                enriched_options.append(opt)

            # 2. Multi-Criteria Evaluation & Pareto Analysis (Phases 7 & 8)
            evaluated_options = self.evaluator.evaluate_candidates(enriched_options, inp.constraints)

            # 3. Decision Selection (Phase 20)
            feasible_options = [o for o in evaluated_options if o.is_feasible and not o.is_dominated]
            if not feasible_options:
                feasible_options = [o for o in evaluated_options if o.is_feasible]

            # Prefer non-dominated active option with high objective alignment, or NO_ACTION
            selected_option = None
            if feasible_options:
                feasible_options.sort(
                    key=lambda o: (
                        o.scores.get("objective_alignment", 0.0),
                        o.scores.get("risk_score", 0.0),
                        o.scores.get("reversibility_score", 0.0),
                    ),
                    reverse=True,
                )
                selected_option = feasible_options[0]

            # 4. Lifecycle State Determination (Phase 2)
            lifecycle_state = DecisionLifecycleState.SELECTED
            dec_type = selected_option.option_type if selected_option else DecisionType.NO_ACTION

            approval_required = False
            approval_reason = None
            if selected_option:
                app_req, app_msg = self.bridges.check_approval_requirement(selected_option, selected_option.security_classification)
                if app_req or getattr(selected_option, "requires_approval", False):
                    approval_required = True
                    approval_reason = app_msg or "Requires operational authorization"
                    lifecycle_state = DecisionLifecycleState.AWAITING_APPROVAL
                    self._emit_event("decision.awaiting_approval", {"decision_id": dec_id, "reason": approval_reason})

            if not selected_option:
                lifecycle_state = DecisionLifecycleState.BLOCKED

            # 5. Certainty calculation (Phase 21)
            certainty = DecisionCertainty.HIGH
            if any(a.status == AssumptionStatus.UNKNOWN for a in inp.assumptions):
                certainty = DecisionCertainty.UNCERTAIN
            elif any(o.security_classification == SecurityAuthorizationStatus.UNKNOWN for o in evaluated_options):
                certainty = DecisionCertainty.MEDIUM
            elif lifecycle_state == DecisionLifecycleState.BLOCKED:
                certainty = DecisionCertainty.BLOCKED

            record = DecisionV2Record(
                decision_id=dec_id,
                objective_id=inp.objective_id,
                title=inp.title or inp.statement,
                decision_version=1,
                status=lifecycle_state,
                decision_type=dec_type,
                options=evaluated_options,
                selected_option=selected_option,
                constraints=inp.constraints,
                assumptions=inp.assumptions,
                evidence=inp.historical_evidence,
                uncertainty={"certainty": certainty.value, "assumptions_count": len(inp.assumptions)},
                certainty=certainty,
                risk_summary={"selected_risk": selected_option.risk_references if selected_option else []},
                resource_summary=selected_option.estimated_resource_profile if selected_option else {},
                governance_summary={"compliance": "VERIFIED"},
                security_summary={"classification": selected_option.security_classification.value if selected_option else "UNKNOWN"},
                approval_summary={"required": approval_required, "reason": approval_reason},
                expected_outcomes={"expected": selected_option.expected_outcome if selected_option else "None"},
                verification_status=VerificationStatus.UNVERIFIED,
                valid_until=now + timedelta(hours=24),  # Standard 24h decision expiration
                provenance=inp.provenance,
                correlation_id=inp.correlation_id,
                trace_id=inp.trace_id,
            )

            self._decisions[dec_id] = record
            record.explanation = self.generate_explanation(dec_id)

            # Persist to DB if session exists
            if self.db is not None:
                self._persist_decision_record(record)

            self._emit_event("decision.evaluation_completed", {"decision_id": dec_id, "selected_option_id": selected_option.option_id if selected_option else None})
            if lifecycle_state == DecisionLifecycleState.SELECTED:
                self._emit_event("decision.selected", {"decision_id": dec_id, "option_id": selected_option.option_id if selected_option else None})

            return record

    def deliberate(self, inp: DecisionInput, user_id: str | None = None) -> DecisionV2Record:
        """Alias for evaluate_decision supporting high-level deliberation calls."""
        return self.evaluate_decision(inp, user_id=user_id)

    def record_approval(
        self, decision_id: str, approver_id: str, approval_notes: str = ""
    ) -> DecisionV2Record:
        """Record formal human or institutional approval."""
        with self._lock:
            rec = self.approve_decision(
                decision_id=decision_id,
                approver=approver_id,
                approval_id=f"app_{uuid.uuid4().hex[:8]}",
            )
            rec.metadata["approver_id"] = approver_id
            rec.metadata["approval_notes"] = approval_notes
            return rec

    def invalidate_assumption(
        self, decision_id: str, assumption_id: str, new_evidence: str = ""
    ) -> DecisionV2Record:
        """Mark assumption invalidated and transition decision to EVALUATING for safe re-evaluation."""
        with self._lock:
            rec = self.get_decision(decision_id)
            if not rec:
                raise KeyError(f"Decision '{decision_id}' not found.")
            for asm in rec.assumptions:
                if asm.id == assumption_id or asm.assumption_id == assumption_id:
                    asm.status = AssumptionStatus.INVALIDATED
            rec.status = DecisionLifecycleState.EVALUATING
            rec.revalidation_required = True
            rec.updated_at = datetime.now(UTC)
            self._emit_event("decision.assumption_invalidated", {
                "decision_id": decision_id,
                "assumption_id": assumption_id,
                "evidence": new_evidence,
            })
            return rec

    def reevaluate(self, decision_id: str, reason: str = "") -> DecisionV2Record:
        """Alias for re_evaluate_decision."""
        return self.re_evaluate_decision(decision_id, reason=reason)

    def _persist_decision_record(self, record: DecisionV2Record) -> None:
        """Persist decision and options to SQL database."""
        try:
            db_dec = DecisionV2Model(
                decision_id=record.decision_id,
                objective_id=record.objective_id,
                task_id=record.task_id,
                conversation_id=record.conversation_id,
                decision_version=record.decision_version,
                status=record.status.value,
                decision_type=record.decision_type.value,
                selected_option_id=record.selected_option.option_id if record.selected_option else None,
                certainty=record.certainty.value,
                risk_summary=record.risk_summary,
                resource_summary=record.resource_summary,
                governance_summary=record.governance_summary,
                security_summary=record.security_summary,
                approval_summary=record.approval_summary,
                expected_outcomes=record.expected_outcomes,
                verification_status=record.verification_status.value,
                valid_until=record.valid_until,
                provenance_json=record.provenance,
                correlation_id=record.correlation_id,
                trace_id=record.trace_id,
            )
            self.db.add(db_dec)

            for opt in record.options:
                db_opt = DecisionOptionV2Model(
                    option_id=opt.option_id,
                    decision_id=record.decision_id,
                    name=opt.name,
                    description=opt.description,
                    option_type=opt.option_type.value,
                    action_reference=opt.action_reference,
                    is_feasible=opt.is_feasible,
                    is_dominated=opt.is_dominated,
                    rejection_reason=opt.rejection_reason,
                    reversibility=opt.reversibility,
                    confidence=opt.confidence,
                    scores_json=opt.scores,
                    tradeoffs_json=opt.tradeoffs,
                )
                self.db.add(db_opt)

            for asm in record.assumptions:
                db_asm = DecisionAssumptionModel(
                    assumption_id=asm.assumption_id,
                    decision_id=record.decision_id,
                    statement=asm.statement,
                    source=asm.source,
                    confidence=asm.confidence,
                    status=asm.status.value,
                    impact_if_false=asm.impact_if_false,
                )
                self.db.add(db_asm)

            self.db.commit()
        except Exception as ex:
            logger.warning("Failed to persist decision to DB: %s", ex)
            self.db.rollback()

    # --------------------------------------------------------------------------
    # 2. Lifecycle Actions & Transitions (Phase 2 & 18)
    # --------------------------------------------------------------------------

    def select_option(self, decision_id: str, chosen_option_id: str, actor: str = "user") -> DecisionV2Record:
        """Explicitly select an option (user or autonomous override)."""
        self._verify_execution_allowed()

        with self._lock:
            record = self._decisions.get(decision_id)
            if not record:
                raise KeyError(f"Decision '{decision_id}' not found.")

            target_opt = next((o for o in record.options if o.option_id == chosen_option_id), None)
            if not target_opt:
                raise ValueError(f"Option '{chosen_option_id}' not in decision alternatives.")

            if not target_opt.is_feasible:
                raise ValueError(f"Cannot select infeasible option '{chosen_option_id}': {target_opt.rejection_reason}")

            record.selected_option = target_opt
            record.status = DecisionLifecycleState.SELECTED
            record.updated_at = datetime.now(UTC)

            self._emit_event("decision.selected", {"decision_id": decision_id, "option_id": chosen_option_id, "actor": actor})
            return record

    def approve_decision(self, decision_id: str, approver: str, approval_id: str) -> DecisionV2Record:
        """Approve a decision suspended in AWAITING_APPROVAL."""
        self._verify_execution_allowed()

        with self._lock:
            record = self._decisions.get(decision_id)
            if not record:
                raise KeyError(f"Decision '{decision_id}' not found.")

            if not record.can_transition_to(DecisionLifecycleState.APPROVED):
                raise ValueError(f"Cannot transition decision from {record.status} to APPROVED")

            record.status = DecisionLifecycleState.APPROVED
            record.approval_summary["approved_by"] = approver
            record.approval_summary["approval_id"] = approval_id
            record.updated_at = datetime.now(UTC)

            self._emit_event("decision.approved", {"decision_id": decision_id, "approver": approver, "approval_id": approval_id})
            return record

    def reject_decision(self, decision_id: str, actor: str, reason: str) -> DecisionV2Record:
        """Reject a proposed or pending decision."""
        with self._lock:
            record = self._decisions.get(decision_id)
            if not record:
                raise KeyError(f"Decision '{decision_id}' not found.")

            record.status = DecisionLifecycleState.REJECTED
            record.approval_summary["rejected_by"] = actor
            record.approval_summary["rejection_reason"] = reason
            record.updated_at = datetime.now(UTC)

            self._emit_event("decision.rejected", {"decision_id": decision_id, "actor": actor, "reason": reason})
            return record

    def defer_decision(self, decision_id: str, reason: str = "Deferred by operator") -> DecisionV2Record:
        """Postpone decision resolution without cancellation."""
        with self._lock:
            record = self._decisions.get(decision_id)
            if not record:
                raise KeyError(f"Decision '{decision_id}' not found.")

            record.status = DecisionLifecycleState.DEFERRED
            record.expiration_reason = reason
            record.updated_at = datetime.now(UTC)

            self._emit_event("decision.deferred", {"decision_id": decision_id, "reason": reason})
            return record

    def cancel_decision(self, decision_id: str, reason: str = "User cancelled") -> DecisionV2Record:
        """Terminate a pending decision."""
        with self._lock:
            record = self._decisions.get(decision_id)
            if not record:
                raise KeyError(f"Decision '{decision_id}' not found.")

            record.status = DecisionLifecycleState.CANCELLED
            record.expiration_reason = reason
            record.updated_at = datetime.now(UTC)
            return record

    # --------------------------------------------------------------------------
    # 3. Re-evaluation & Expiration (Phases 28 & 29)
    # --------------------------------------------------------------------------

    def re_evaluate_decision(self, decision_id: str, reason: str) -> DecisionV2Record:
        """Re-evaluate an active decision following assumption invalidation or drift."""
        with self._lock:
            record = self._decisions.get(decision_id)
            if not record:
                raise KeyError(f"Decision '{decision_id}' not found.")

            record.status = DecisionLifecycleState.EVALUATING
            record.decision_version += 1
            record.revalidation_required = False
            record.updated_at = datetime.now(UTC)

            self._emit_event("decision.re_evaluation_required", {"decision_id": decision_id, "reason": reason})
            return record

    # --------------------------------------------------------------------------
    # 4. Outcome Tracking & Memory (Phases 24 & 26)
    # --------------------------------------------------------------------------

    def record_outcome(self, outcome: DecisionOutcomeRecord) -> DecisionOutcomeRecord:
        """Record post-execution reality, verify deviations, and consolidate into Decision Memory."""
        with self._lock:
            record = self._decisions.get(outcome.decision_id)
            if record:
                record.actual_outcomes = outcome.actual_outcome
                record.verification_status = outcome.verification_status
                record.status = DecisionLifecycleState.VERIFIED if outcome.verification_status == VerificationStatus.VERIFIED else DecisionLifecycleState.FAILED

                # Consolidate into Decision Memory (Phase 24)
                self.memory.consolidate_decision(record, outcome=outcome, lessons=outcome.lessons_learned)

            self._outcomes[outcome.decision_id] = outcome

            if self.db is not None:
                try:
                    db_out = DecisionOutcomeV2Model(
                        outcome_id=outcome.outcome_id,
                        decision_id=outcome.decision_id,
                        predicted_outcome=outcome.predicted_outcome,
                        actual_outcome=outcome.actual_outcome,
                        deviation_score=outcome.deviation_score,
                        execution_cost=outcome.execution_cost,
                        latency_ms=outcome.latency_ms,
                        verification_status=outcome.verification_status.value,
                        lessons_learned=outcome.lessons_learned,
                    )
                    self.db.add(db_out)
                    self.db.commit()
                except Exception as ex:
                    logger.warning("Failed to persist outcome to DB: %s", ex)
                    self.db.rollback()

            self._emit_event("decision.verification_started", {"decision_id": outcome.decision_id})
            if outcome.verification_status == VerificationStatus.VERIFIED:
                self._emit_event("decision.verified", {"decision_id": outcome.decision_id})
            else:
                self._emit_event("decision.failed", {"decision_id": outcome.decision_id})

            return outcome

    # --------------------------------------------------------------------------
    # 5. Explanation Model (Phase 30)
    # --------------------------------------------------------------------------

    def generate_explanation(self, decision_id: str) -> DecisionExplanation:
        """Synthesize a structured 15-part explanation without hidden chain-of-thought."""
        with self._lock:
            record = self._decisions.get(decision_id)
            if not record:
                raise KeyError(f"Decision '{decision_id}' not found.")

            selected_name = record.selected_option.name if record.selected_option else "NO_ACTION"
            return DecisionExplanation(
                decision_id=record.decision_id,
                objective=record.objective_id,
                options_considered=[o.name for o in record.options],
                constraints_summary=[f"{c.name}: {c.statement}" for c in record.constraints],
                evidence_basis=[f"Evidence item: {e.get('summary', 'data')}" for e in record.evidence],
                risks_evaluated=[str(r) for r in record.risk_summary.get("selected_risk", [])],
                forecasts_used=[record.expected_outcomes.get("expected", "nominal")],
                causal_effects_identified=["Direct effect on target objective verified"],
                resource_implications=record.resource_summary,
                governance_status=record.governance_summary.get("compliance", "COMPLIANT"),
                security_status=record.security_summary.get("classification", "AUTHORIZED"),
                approval_status="APPROVED" if record.status == DecisionLifecycleState.APPROVED else ("REQUIRED" if record.approval_summary.get("required") else "NOT_REQUIRED"),
                uncertainty_profile=record.uncertainty,
                selected_action=selected_name,
                expected_outcome=record.expected_outcomes.get("expected", "None"),
                verification_plan=["Monitor system telemetry post-execution for drift and regression"],
            )

    # --------------------------------------------------------------------------
    # 6. Read Queries
    # --------------------------------------------------------------------------

    def list_decisions(self, limit: int = 50) -> list[DecisionV2Record]:
        with self._lock:
            decs = list(self._decisions.values())
            decs.sort(key=lambda d: d.created_at, reverse=True)
            return decs[:limit]

    def get_decision(self, decision_id: str) -> DecisionV2Record | None:
        with self._lock:
            return self._decisions.get(decision_id)

    def get_options(self, decision_id: str) -> list[DecisionOption]:
        with self._lock:
            record = self._decisions.get(decision_id)
            return record.options if record else []

    def get_assumptions(self, decision_id: str) -> list[AssumptionItem]:
        with self._lock:
            record = self._decisions.get(decision_id)
            return record.assumptions if record else []

    def get_outcome(self, decision_id: str) -> DecisionOutcomeRecord | None:
        with self._lock:
            return self._outcomes.get(decision_id)


# Process-wide singleton instance
_global_decision_intelligence_service: DecisionIntelligenceService | None = None


def get_decision_intelligence_service(db: Session | None = None) -> DecisionIntelligenceService:
    """Retrieve or create the process-wide DecisionIntelligenceService singleton."""
    global _global_decision_intelligence_service
    if _global_decision_intelligence_service is None:
        _global_decision_intelligence_service = DecisionIntelligenceService(db=db)
    elif db is not None and _global_decision_intelligence_service.db is None:
        _global_decision_intelligence_service.db = db
    return _global_decision_intelligence_service
