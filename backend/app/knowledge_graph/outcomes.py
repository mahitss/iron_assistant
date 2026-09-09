"""Outcome memory modeling and outcome verification (INVARIANTS 63, 64)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Dict, List, Optional
import uuid
from app.knowledge_graph.schemas import OutcomeSchema


class OutcomeManager:
    """Manages recorded workflow and goal outcomes, prioritizing verified results for durable memory."""

    def __init__(self) -> None:
        # outcome_id -> OutcomeSchema
        self._outcomes: Dict[str, OutcomeSchema] = {}

    def record_outcome(
        self,
        related_goal_id: str,
        result: Dict[str, Any],
        evidence: Optional[List[Dict[str, Any]]] = None,
        verified: bool = False,
        user_id: str = "default_user",
    ) -> OutcomeSchema:
        o_id = str(uuid.uuid4())
        out = OutcomeSchema(
            outcome_id=o_id,
            related_goal_id=related_goal_id,
            result=result,
            evidence=evidence or [],
            verified=verified,
            timestamp=datetime.now(UTC),
            user_id=user_id,
        )
        self._outcomes[o_id] = out
        return out

    def get_outcome(self, outcome_id: str) -> Optional[OutcomeSchema]:
        return self._outcomes.get(outcome_id)

    def list_outcomes(self, user_id: Optional[str] = None) -> List[OutcomeSchema]:
        results = list(self._outcomes.values())
        if user_id:
            results = [o for o in results if o.user_id == user_id]
        return results
