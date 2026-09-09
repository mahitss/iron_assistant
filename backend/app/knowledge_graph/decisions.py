"""Decision memory tracking questions, alternatives, rationale references, and owner consensus (INVARIANTS 54-59, 154-156)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Dict, List, Optional
import uuid

from app.knowledge_graph.schemas import (
    DecisionSchema,
    DecisionStatus,
    ScopeType,
)


class DecisionAgreementError(Exception):
    """Raised when an attempt is made to infer agreement solely from discussion without consensus."""
    pass


class DecisionManager:
    """Manages architectural, technical, and project decisions without fabricated rationale."""

    def __init__(self) -> None:
        # decision_id -> DecisionSchema
        self._decisions: Dict[str, DecisionSchema] = {}

    def record_decision(
        self,
        question: str,
        decision: str,
        alternatives: Optional[List[str]] = None,
        rationale_reference: Optional[str] = None,
        owner: str = "user",
        scope: ScopeType = ScopeType.PROJECT,
        confidence: float = 1.0,
        user_id: str = "default_user",
        project_id: Optional[str] = None,
        is_only_discussion: bool = False,
    ) -> DecisionSchema:
        """Records a verified decision.

        INVARIANT 59: Never infer agreement solely from discussion!
        INVARIANT 156: If rationale was not recorded, say unknown rather than fabricating claims.
        """
        if is_only_discussion:
            raise DecisionAgreementError(
                "Cannot record decision: discussion alone does not constitute verified agreement or consensus."
            )

        clean_rationale = rationale_reference.strip() if rationale_reference else "Rationale: UNKNOWN (not recorded)"

        d_id = str(uuid.uuid4())
        dec = DecisionSchema(
            decision_id=d_id,
            question=question.strip(),
            decision=decision.strip(),
            alternatives=alternatives or [],
            rationale_reference=clean_rationale,
            owner=owner.strip(),
            timestamp=datetime.now(UTC),
            scope=scope,
            confidence=min(max(confidence, 0.0), 1.0),
            status=DecisionStatus.ACTIVE,
            user_id=user_id,
            project_id=project_id,
        )

        self._decisions[d_id] = dec
        return dec

    def supersede_decision(self, old_decision_id: str, new_decision_id: str) -> DecisionSchema:
        """INVARIANT 56: Do not silently overwrite old decisions. Mark as SUPERSEDED."""
        old = self._decisions.get(old_decision_id)
        if not old:
            raise ValueError(f"Decision '{old_decision_id}' not found.")
        old.status = DecisionStatus.SUPERSEDED
        return old

    def explain_decision(self, decision_id: str) -> Dict[str, Any]:
        """INVARIANT 154 & 155: Explains why a decision was made with date, source, alternatives, and rationale."""
        dec = self._decisions.get(decision_id)
        if not dec:
            return {"error": f"Decision '{decision_id}' not found."}

        return {
            "decision_id": dec.decision_id,
            "question": dec.question,
            "chosen_decision": dec.decision,
            "alternatives_considered": dec.alternatives,
            "rationale": dec.rationale_reference,
            "owner": dec.owner,
            "timestamp": dec.timestamp.isoformat(),
            "status": dec.status.value,
        }

    def list_decisions(
        self,
        project_id: Optional[str] = None,
        user_id: Optional[str] = None,
        status: Optional[DecisionStatus] = None,
    ) -> List[DecisionSchema]:
        results = list(self._decisions.values())
        if project_id:
            results = [d for d in results if d.project_id == project_id]
        if user_id:
            results = [d for d in results if d.user_id == user_id]
        if status:
            results = [d for d in results if d.status == status]
        return results
