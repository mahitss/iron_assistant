"""Causal Event Timeline Normalization (Task 55, Prompts #20-#25)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.causal.temporal import parse_utc, utc_now


class CausalEvent(BaseModel):
    event_id: str
    event_type: str  # DEPLOYMENT, CONFIG_CHANGE, TRAFFIC_SPIKE, FAILURE, RESTART
    entity: str
    description: str
    timestamp: datetime = Field(default_factory=utc_now)
    source: str
    details: dict[str, Any] = Field(default_factory=dict)


class CausalEventAligner:
    """Aligns and chronological-orders multi-source environmental and system events."""

    @staticmethod
    def align_timeline(events: list[CausalEvent]) -> list[CausalEvent]:
        """Returns deterministic, chronological timeline of causal events."""
        return sorted(events, key=lambda e: (parse_utc(e.timestamp), e.event_id))
