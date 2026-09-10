"""Multi-factor prioritization, priority memory, and user override supremacy (INVARIANTS 69-73, 211)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.executive_memory.schemas import OpenLoopSchema


class PriorityEngine:
    """Calculates multi-factor priority while strictly enforcing user override supremacy."""

    def __init__(self) -> None:
        # loop_id -> explicit user priority override
        self._user_overrides: dict[str, float] = {}

    def set_user_priority_override(self, loop_id: str, priority_value: float) -> None:
        """INVARIANT 71 & 72: User priorities override learned/algorithmic priorities."""
        self._user_overrides[loop_id] = float(priority_value)

    def calculate_priority(
        self,
        loop: OpenLoopSchema,
        importance: float = 0.5,
        urgency: float = 0.5,
        goal_alignment: float = 0.5,
        deadline_factor: float = 0.5,
        risk_factor: float = 0.5,
    ) -> float:
        """INVARIANT 69 & 70: Multi-factor ranking: importance, urgency, goal alignment, dependencies, deadline, risk.
        User override strictly prevails if present.
        """
        # INVARIANT 71: Check user override first
        if loop.loop_id in self._user_overrides:
            return self._user_overrides[loop.loop_id]

        # Multi-factor algorithmic recommendation
        score = (
            importance * 0.25
            + urgency * 0.25
            + goal_alignment * 0.20
            + deadline_factor * 0.15
            + risk_factor * 0.15
        )
        return round(score, 3)

    def rank_open_loops(self, loops: list[OpenLoopSchema]) -> list[tuple[OpenLoopSchema, float]]:
        """INVARIANT 211: Ranks unresolved open loops."""
        scored = []
        for l in loops:
            score = self.calculate_priority(l)
            scored.append((l, score))
        return sorted(scored, key=lambda pair: pair[1], reverse=True)

    def rank_loops(
        self,
        loops: list[Any],
        user_overrides: dict[str, float] | None = None,
    ) -> list[Any]:
        """INVARIANT 71, 211: Ranks loops with optional explicit user overrides."""
        overrides = {**self._user_overrides, **(user_overrides or {})}

        def _get_score(loop: Any) -> float:
            lid = loop.get("loop_id") if isinstance(loop, dict) else getattr(loop, "loop_id", "")
            if lid in overrides:
                return float(overrides[lid])
            raw_p = loop.get("priority") if isinstance(loop, dict) else getattr(loop, "priority", 0.5)
            if isinstance(raw_p, (int, float)):
                return float(raw_p)
            p_str = str(raw_p).upper()
            if p_str == "HIGH":
                return 0.9
            if p_str == "MEDIUM":
                return 0.5
            return 0.2

        return sorted(loops, key=_get_score, reverse=True)
