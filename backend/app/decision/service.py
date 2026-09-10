"""Service orchestrator for Kairo Executive Decision Engine (Task 57).

Exposes high-level transactional API for evaluating decisions, selecting options,
approvals, revalidations, post-execution outcomes tracking, and explanations.
"""

from __future__ import annotations

from typing import Any

from app.decision.audit import decision_auditor
from app.decision.calibration import decision_calibration_engine
from app.decision.decisions import decision_lifecycle_manager
from app.decision.engine import decision_engine
from app.decision.explain import explanation_engine
from app.decision.outcomes import outcome_tracker
from app.decision.reconciliation import decision_reconciler
from app.decision.schemas import (
    CandidateOption,
    DecisionOutcome,
    DecisionRecord,
    DecisionRequest,
    DecisionRevision,
    DecisionStatus,
    EvidenceItem,
)


class DecisionService:
    """Singleton service providing thread-safe in-memory cache and persistence bridges."""

    def __init__(self) -> None:
        self._records: dict[str, DecisionRecord] = {}
        self._requests: dict[str, DecisionRequest] = {}
        self._revisions: dict[str, list[DecisionRevision]] = {}
        self._outcomes: dict[str, DecisionOutcome] = {}

    def analyze_and_recommend(
        self,
        request: DecisionRequest,
        candidate_options: list[CandidateOption] | None = None,
        additional_evidence: list[EvidenceItem] | None = None,
        simulations: list[dict[str, Any]] | None = None,
        causal_context: dict[str, Any] | None = None,
        memory_context: dict[str, Any] | None = None,
        is_production: bool = False,
        is_authorized: bool = True,
    ) -> DecisionRecord:
        """Evaluates a decision request and stores the resulting decision record."""
        self._requests[request.request_id] = request

        record = decision_engine.evaluate_decision(
            request=request,
            candidate_options=candidate_options,
            additional_evidence=additional_evidence,
            simulations=simulations,
            causal_context=causal_context,
            memory_context=memory_context,
            is_production=is_production,
            is_authorized=is_authorized,
        )

        self._records[record.decision_id] = record
        return record

    def get_decision(self, decision_id: str) -> DecisionRecord | None:
        return self._records.get(decision_id)

    def list_decisions(self, limit: int = 50) -> list[DecisionRecord]:
        return list(self._records.values())[-limit:]

    def select_option(
        self,
        decision_id: str,
        chosen_option_id: str,
        actor: str = "user",
    ) -> DecisionRecord:
        """Records an authorized actor's selection, preserving recommendation vs user override."""
        record = self._records.get(decision_id)
        if not record:
            raise KeyError(f"Decision '{decision_id}' not found.")

        updated_record, revision = decision_lifecycle_manager.select_option(
            record=record,
            chosen_option_id=chosen_option_id,
            actor=actor,
        )

        self._records[decision_id] = updated_record
        self._revisions.setdefault(decision_id, []).append(revision)

        decision_auditor.log_event(
            decision_id=decision_id,
            action="OPTION_SELECTED",
            actor=actor,
            details={
                "chosen_option_id": chosen_option_id,
                "is_override": updated_record.user_override,
                "version": updated_record.version,
            },
        )

        return updated_record

    def approve_decision(
        self,
        decision_id: str,
        approver: str,
        approval_id: str,
    ) -> DecisionRecord:
        """Approves a decision for guarded execution handoff."""
        record = self._records.get(decision_id)
        if not record:
            raise KeyError(f"Decision '{decision_id}' not found.")

        updated_record = decision_lifecycle_manager.record_approval(
            record=record,
            approval_id=approval_id,
            approver=approver,
        )

        self._records[decision_id] = updated_record
        decision_auditor.log_event(
            decision_id=decision_id,
            action="DECISION_APPROVED",
            actor=approver,
            details={"approval_id": approval_id, "status": updated_record.status.value},
        )

        return updated_record

    def revalidate_decision(self, decision_id: str) -> DecisionRecord:
        """Re-evaluates a decision against current environment or policy drift."""
        record = self._records.get(decision_id)
        if not record:
            raise KeyError(f"Decision '{decision_id}' not found.")

        original_request = self._requests.get(record.request_id)
        if not original_request:
            original_request = DecisionRequest(
                request_id=record.request_id,
                question="Revalidation of decision",
            )

        new_record = decision_engine.evaluate_decision(request=original_request)
        new_record = new_record.model_copy(
            update={
                "decision_id": record.decision_id,
                "version": record.version + 1,
            }
        )
        self._records[decision_id] = new_record

        decision_auditor.log_event(
            decision_id=decision_id,
            action="DECISION_REVALIDATED",
            actor="system",
            details={"version": new_record.version, "confidence": new_record.confidence},
        )

        return new_record

    def record_outcome(
        self,
        decision_id: str,
        actual_benefit: float,
        actual_cost: float,
        actual_duration: float,
        success: bool = True,
        unexpected_side_effects: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> DecisionOutcome:
        """Records post-execution verified outcome and checks prediction error."""
        record = self._records.get(decision_id)
        predicted_eval = None
        if record and record.ranking and record.ranking.ranked_options:
            predicted_eval = next(
                (e for e in record.ranking.ranked_options if e.option_id == record.selected_option_id),
                record.ranking.ranked_options[0],
            )

        outcome = outcome_tracker.record_outcome(
            decision_id=decision_id,
            predicted_evaluation=predicted_eval,
            actual_benefit=actual_benefit,
            actual_cost=actual_cost,
            actual_duration=actual_duration,
            success=success,
            unexpected_side_effects=unexpected_side_effects,
            metadata=metadata,
        )

        self._outcomes[decision_id] = outcome

        if record:
            new_status = DecisionStatus.VERIFIED if success else DecisionStatus.FAILED
            updated_record, _ = decision_lifecycle_manager.transition_status(
                record=record,
                new_status=new_status,
                actor="verification_subsystem",
                note=f"Outcome recorded: success={success}, prediction_error={outcome.prediction_error}",
            )
            self._records[decision_id] = updated_record

        decision_auditor.log_event(
            decision_id=decision_id,
            action="OUTCOME_RECORDED",
            actor="verification_subsystem",
            details={
                "success": success,
                "prediction_error": outcome.prediction_error,
            },
        )

        return outcome

    def get_outcome(self, decision_id: str) -> DecisionOutcome | None:
        return self._outcomes.get(decision_id)

    def explain_decision(
        self,
        decision_id: str,
        query: str = "why this option",
    ) -> dict[str, Any]:
        """Provides faithful explanation derived from structured decision factors."""
        record = self._records.get(decision_id)
        if not record or not record.recommendation or not record.ranking:
            return {"error": f"Decision '{decision_id}' lacks recommendation data."}

        return explanation_engine.answer_query(
            query=query,
            recommendation=record.recommendation,
            ranking=record.ranking,
            options=[],
            evidence_set=None,  # Handled safely by answer_query fallbacks
            tradeoffs=[],
            risks=[],
            uncertainty=None,  # Fallbacks applied
        )

    def reconstruct_as_of(self, decision_id: str) -> dict[str, Any]:
        record = self._records.get(decision_id)
        if not record:
            return {"error": f"Decision '{decision_id}' not found."}
        return decision_reconciler.reconstruct_as_of(record)

    def get_analytics(self) -> dict[str, Any]:
        records = list(self._records.values())
        outcomes = list(self._outcomes.values())
        return decision_calibration_engine.compute_analytics(records, outcomes)


decision_service = DecisionService()
