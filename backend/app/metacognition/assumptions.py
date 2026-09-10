"""Assumption modeling, impact classification, and verification gating (INVARIANTS 32-35)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Dict, List, Optional
import uuid

from app.metacognition.schemas import AssumptionImpact, AssumptionSchema


class AssumptionTracker:
    """Tracks traceable operational assumptions and gates high-impact assumptions for confirmation."""

    def __init__(self) -> None:
        # assumption_id -> AssumptionSchema
        self._assumptions: Dict[str, AssumptionSchema] = {}

    def record_assumption(
        self,
        statement: str,
        originating_goal_id: Optional[str] = None,
        impact: AssumptionImpact = AssumptionImpact.MEDIUM,
    ) -> AssumptionSchema:
        """INVARIANTS 33 & 34: Every material assumption must be traceable and classified by impact."""
        a_id = str(uuid.uuid4())
        rec = AssumptionSchema(
            assumption_id=a_id,
            statement=statement.strip(),
            originating_goal_id=originating_goal_id,
            impact=impact,
            is_validated=False,
            validation_evidence=None,
            created_at=datetime.now(UTC),
        )
        self._assumptions[a_id] = rec
        return rec

    def validate_assumption(self, assumption_id: str, evidence: str) -> AssumptionSchema:
        assump = self._assumptions.get(assumption_id)
        if not assump:
            raise ValueError(f"Assumption '{assumption_id}' not found.")
        assump.is_validated = True
        assump.validation_evidence = evidence
        return assump

    def list_assumptions(
        self,
        originating_goal_id: Optional[str] = None,
        only_unvalidated: bool = False,
    ) -> List[AssumptionSchema]:
        recs = list(self._assumptions.values())
        if originating_goal_id:
            recs = [r for r in recs if r.originating_goal_id == originating_goal_id]
        if only_unvalidated:
            recs = [r for r in recs if not r.is_validated]
        return recs

    def requires_confirmation(self, assumption: AssumptionSchema) -> bool:
        """INVARIANT 35: High and Critical impact assumptions require explicit user confirmation or verification."""
        return not assumption.is_validated and assumption.impact in (
            AssumptionImpact.HIGH.value,
            AssumptionImpact.CRITICAL.value,
        )
