"""Assumption Modeling, Impact Classification, and Transparency Tracking (Task 48)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
import uuid

from app.intent.schemas import AssumptionType

logger = logging.getLogger("kairo.intent.assumptions")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class Assumption:
    """Explicitly modeled assumption preventing silent unverified extrapolations (Spec 50-54)."""

    statement: str
    source: AssumptionType = AssumptionType.INFERRED
    confidence: float = 0.7
    impact: str = "LOW"  # LOW, MEDIUM, HIGH, CRITICAL
    status: str = "ACTIVE"  # ACTIVE, CONFIRMED, REJECTED
    assumption_id: str = field(default_factory=lambda: f"assump_{uuid.uuid4().hex[:8]}")
    created_at: datetime = field(default_factory=utc_now)

    @property
    def is_high_impact(self) -> bool:
        """Enforce Spec 52: If assumption materially changes outcome, ask user."""
        return self.impact in ("HIGH", "CRITICAL")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "assumption_id": self.assumption_id,
            "statement": self.statement,
            "source": self.source.value if hasattr(self.source, "value") else str(self.source),
            "confidence": round(self.confidence, 3),
            "impact": self.impact,
            "is_high_impact": self.is_high_impact,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
        }


class AssumptionTracker:
    """Manages intent assumptions and ensures transparency before execution (Spec 50-54)."""

    def __init__(self) -> None:
        # assumption_id -> Assumption
        self._assumptions: Dict[str, Assumption] = {}

    def record_assumption(
        self,
        statement: str,
        source: AssumptionType = AssumptionType.INFERRED,
        confidence: float = 0.7,
        impact: str = "LOW",
    ) -> Assumption:
        a = Assumption(
            statement=statement,
            source=source,
            confidence=confidence,
            impact=impact,
        )
        self._assumptions[a.assumption_id] = a
        if a.is_high_impact:
            logger.warning("HIGH-IMPACT ASSUMPTION RECORDED: '%s' (source=%s)", statement, source.value)
        return a

    def get_high_impact_assumptions(self) -> List[Assumption]:
        return [a for a in self._assumptions.values() if a.is_high_impact and a.status == "ACTIVE"]

    def list_assumptions(self) -> List[Assumption]:
        return list(self._assumptions.values())
