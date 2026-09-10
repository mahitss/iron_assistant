"""Decision lifecycle, state transitions, and revision management for Task 57.

Maintains immutable decision records, distinguishes engine recommendation from
user decision, preserves overrides, and handles decision revisions.
"""

from __future__ import annotations

import copy
from datetime import datetime, timezone
from typing import Any

from app.decision.schemas import (
    DecisionGate,
    DecisionRanking,
    DecisionRecord,
    DecisionRequest,
    DecisionRevision,
    DecisionStatus,
    GateEvaluationStatus,
    Recommendation,
)


class DecisionLifecycleManager:
    """Controls lifecycle transitions and immutable versioned revisions."""

    def create_record(
        self,
        request: DecisionRequest,
        recommendation: Recommendation,
        ranking: DecisionRanking,
        gates: dict[str, DecisionGate],
        approval_required: bool,
        provenance: dict[str, Any],
    ) -> DecisionRecord:
        now = datetime.now(timezone.utc)

        status = DecisionStatus.AWAITING_APPROVAL if approval_required else DecisionStatus.RECOMMENDED

        return DecisionRecord(
            decision_id=f"dec_{request.request_id.split('_')[-1]}",
            request_id=request.request_id,
            status=status,
            recommendation=recommendation,
            selected_option_id=recommendation.recommended_option_id,
            selected_by="engine_recommendation",
            user_override=False,
            confidence=ranking.confidence,
            ranking=ranking,
            decision_gates=gates,
            approval_required=approval_required,
            approval_id=None,
            execution_plan=recommendation.proposed_execution_plan,
            verification_plan=recommendation.verification_criteria,
            version=1,
            provenance=provenance,
            created_at=now,
            updated_at=now,
        )

    def select_option(
        self,
        record: DecisionRecord,
        chosen_option_id: str,
        actor: str,
    ) -> tuple[DecisionRecord, DecisionRevision]:
        """Authorized actor selects an option. Distinguishes recommendation from decision."""
        old_snapshot = record.model_dump()
        now = datetime.now(timezone.utc)

        # Check if this represents an override
        is_override = (
            record.recommendation is not None
            and chosen_option_id != record.recommendation.recommended_option_id
        )

        new_status = DecisionStatus.AWAITING_APPROVAL if record.approval_required else DecisionStatus.DECIDED

        updated_record = record.model_copy(
            update={
                "selected_option_id": chosen_option_id,
                "selected_by": actor,
                "user_override": is_override,
                "status": new_status,
                "version": record.version + 1,
                "updated_at": now,
            }
        )

        revision = DecisionRevision(
            parent_decision_id=record.decision_id,
            revision_number=record.version + 1,
            reason=f"Option selected by {actor}" + (" (USER OVERRIDE)" if is_override else ""),
            actor=actor,
            previous_snapshot=old_snapshot,
            new_snapshot=updated_record.model_dump(),
            created_at=now,
        )

        return updated_record, revision

    def record_approval(
        self,
        record: DecisionRecord,
        approval_id: str,
        approver: str,
    ) -> DecisionRecord:
        """Approves a decision for execution handoff."""
        if not record.approval_required:
            return record

        now = datetime.now(timezone.utc)
        updated_gates = copy.deepcopy(record.decision_gates)
        if "gate_8_approval" in updated_gates:
            updated_gates["gate_8_approval"].status = GateEvaluationStatus.PASSED
            updated_gates["gate_8_approval"].message = f"Approved by {approver} (ID: {approval_id})"

        return record.model_copy(
            update={
                "approval_id": approval_id,
                "status": DecisionStatus.APPROVED,
                "decision_gates": updated_gates,
                "updated_at": now,
            }
        )

    def transition_status(
        self,
        record: DecisionRecord,
        new_status: DecisionStatus,
        actor: str = "system",
        note: str = "",
    ) -> tuple[DecisionRecord, DecisionRevision | None]:
        """Transitions decision status safely (e.g. EXECUTING, VERIFYING, VERIFIED)."""
        old_snapshot = record.model_dump()
        now = datetime.now(timezone.utc)

        updated_record = record.model_copy(
            update={
                "status": new_status,
                "version": record.version + 1,
                "updated_at": now,
            }
        )

        revision = DecisionRevision(
            parent_decision_id=record.decision_id,
            revision_number=record.version + 1,
            reason=f"Status transitioned to {new_status.value}: {note}" if note else f"Transitioned to {new_status.value}",
            actor=actor,
            previous_snapshot=old_snapshot,
            new_snapshot=updated_record.model_dump(),
            created_at=now,
        )

        return updated_record, revision


decision_lifecycle_manager = DecisionLifecycleManager()
