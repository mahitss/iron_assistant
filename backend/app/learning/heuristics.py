"""Planning and operational heuristic management with conflict resolution (INVARIANTS 68-73)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
import uuid

from app.learning.schemas import GeneralizationScope, HeuristicSchema


class HeuristicPolicyInferenceError(Exception):
    """Raised when an attempt is made to disguise an immutable policy rule as a learned heuristic."""
    pass


class HeuristicManager:
    """Manages creation, conflict resolution, and priority arbitration for operational heuristics."""

    def __init__(self) -> None:
        # heuristic_id -> HeuristicSchema
        self._heuristics: dict[str, HeuristicSchema] = {}

    def register_heuristic(
        self,
        condition: str,
        recommendation: str,
        evidence: list[dict[str, Any]],
        confidence: float = 0.7,
        scope: GeneralizationScope = GeneralizationScope.TASK,
        priority: int = 1,
    ) -> HeuristicSchema:
        """INVARIANT 68-70: Creates an operational heuristic backed by empirical evidence.
        Rejects unsupported heuristics.
        """
        if not evidence:
            raise ValueError("INVARIANT 70: Cannot promote unsupported heuristic without empirical evidence.")

        # INVARIANT 73: The learning engine must never infer policy
        cond_lower = condition.lower()
        rec_lower = recommendation.lower()
        if "policy" in rec_lower or "security_center" in rec_lower or "grant authorization" in rec_lower:
            raise HeuristicPolicyInferenceError(
                "INVARIANT 73: Learning engine must never infer or create security/authorization policy rules."
            )

        hid = f"heu_{uuid.uuid4().hex[:12]}"
        now = datetime.now(UTC)
        h = HeuristicSchema(
            heuristic_id=hid,
            condition=condition.strip(),
            recommendation=recommendation.strip(),
            evidence=evidence,
            confidence=min(max(confidence, 0.1), 1.0),
            scope=scope,
            status="CANDIDATE",
            priority=priority,
            created_at=now,
            updated_at=now,
        )
        self._heuristics[hid] = h
        return h

    def resolve_conflicts(self, context_description: str) -> list[HeuristicSchema]:
        """INVARIANT 71 & 72: Resolves heuristic conflicts by priority, verified evidence strength, and recency."""
        matching = []
        for h in self._heuristics.values():
            if h.status in ("CANDIDATE", "ACTIVE"):
                # Simple keyword matching against condition
                if any(w in context_description.lower() for w in h.condition.lower().split() if len(w) > 3):
                    matching.append(h)

        # INVARIANT 72: Order by priority desc, confidence desc, recency desc
        matching.sort(key=lambda item: (item.priority, item.confidence, item.updated_at), reverse=True)
        return matching

    def get_heuristic(self, heuristic_id: str) -> HeuristicSchema | None:
        return self._heuristics.get(heuristic_id)

    def list_heuristics(
        self,
        scope: GeneralizationScope | None = None,
        status: str | None = None,
    ) -> list[HeuristicSchema]:
        results = list(self._heuristics.values())
        if scope:
            results = [h for h in results if h.scope == scope.value or h.scope == scope]
        if status:
            results = [h for h in results if h.status == status]
        return results
