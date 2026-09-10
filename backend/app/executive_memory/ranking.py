"""Relevance ranking and impact prioritization for executive context (INVARIANT 150)."""

from __future__ import annotations

from typing import Any


class ExecutiveRankingEngine:
    """Ranks context elements surfacing high-impact information first."""

    IMPACT_WEIGHTS = {
        "CRITICAL": 1.0,
        "HIGH": 0.8,
        "MEDIUM": 0.5,
        "LOW": 0.2,
    }

    @classmethod
    def rank_items_by_impact(cls, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """INVARIANT 150: Surface high-impact information first."""
        def score_item(item: dict[str, Any]) -> float:
            impact = str(item.get("impact", "MEDIUM")).upper()
            return cls.IMPACT_WEIGHTS.get(impact, 0.5)

        return sorted(items, key=score_item, reverse=True)
