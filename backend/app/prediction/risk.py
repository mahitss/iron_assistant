"""Predicted Risk Modeling, Candidate Mitigations, and Governance Gating (Task 47)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
import uuid

logger = logging.getLogger("kairo.prediction.risk")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class PredictedRisk:
    """Anticipated environmental risk with candidate mitigations (Spec 41-46).
    
    CRITICAL INVARIANT: Risk != Fact! (Spec 42)
    Predicted risk means 'this may happen', NOT 'this will happen'.
    """

    subject: str
    event: str
    likelihood: float
    impact: float
    timeframe: Any
    confidence: float
    evidence: Any = field(default_factory=list)
    mitigations: List[str] = field(default_factory=list)
    risk_id: str = field(default_factory=lambda: f"risk_{uuid.uuid4().hex[:8]}")
    created_at: datetime = field(default_factory=utc_now)
    scope: Dict[str, Any] = field(default_factory=dict)

    @property
    def risk_score(self) -> float:
        """Normalized risk score 0.0 to 1.0 (Spec 43, 44)."""
        return round(self.likelihood * self.impact, 4)

    def is_high_risk(self) -> bool:
        return self.risk_score >= 0.5

    def to_dict(self) -> Dict[str, Any]:
        return {
            "risk_id": self.risk_id,
            "subject": self.subject,
            "event": self.event,
            "likelihood": round(self.likelihood, 4),
            "impact": round(self.impact, 4),
            "risk_score": self.risk_score,
            "timeframe": self.timeframe.value if hasattr(self.timeframe, "value") else str(self.timeframe),
            "confidence": round(self.confidence, 4),
            "evidence": self.evidence,
            "mitigations": self.mitigations,
            "created_at": self.created_at.isoformat(),
            "scope": self.scope,
            "is_high_risk": self.is_high_risk(),
        }


class RiskAnticipator:
    """Identifies anticipated failure points, capacity exhausts, and candidate mitigations (Spec 41-46)."""

    @classmethod
    def evaluate_risk(
        cls,
        subject: str,
        event: str,
        likelihood: float,
        impact: float,
        timeframe: Any = "short-term",
        confidence: float = 0.5,
        evidence: Any = None,
        candidate_mitigations: Optional[List[str]] = None,
        scope: Optional[Dict[str, Any]] = None,
    ) -> PredictedRisk:
        """Formulate predicted risk. Mitigation execution strictly requires policy & authorization (Spec 46)."""
        rid = f"risk_{uuid.uuid4().hex[:8]}"

        mits = list(candidate_mitigations) if candidate_mitigations else []
        if not mits:
            if "capacity" in event.lower() or "storage" in event.lower():
                mits.append("Trigger diagnostic prune candidate (requires_approval=True)")
                mits.append("Provision additional storage volume (action=scale_storage, requires_approval=True)")
            elif "latency" in event.lower() or "degradation" in event.lower():
                mits.append("Warm query cache (action=cache_warm, requires_approval=False)")
                mits.append("Scale replica count (action=scale_pods, requires_approval=True)")
            else:
                mits.append("Prepare rollback plan (action=plan_rollback, requires_approval=True)")
                mits.append("Collect diagnostic memory dump (action=collect_diag, requires_approval=False)")

        risk = PredictedRisk(
            risk_id=rid,
            subject=subject,
            event=event,
            likelihood=max(0.0, min(1.0, likelihood)),
            impact=max(0.0, min(1.0, impact)),
            timeframe=timeframe,
            confidence=max(0.0, min(1.0, confidence)),
            evidence=evidence or [],
            mitigations=mits,
            scope=scope or {},
        )
        logger.info("Evaluated predicted risk %s on %s: score=%.2f (conf=%.2f)", rid, subject, risk.risk_score, confidence)
        return risk

    @classmethod
    def assess_risk(
        cls,
        subject: str,
        event: str,
        likelihood: float,
        impact: float,
        timeframe: Any = "short-term",
        confidence: float = 0.5,
        evidence: Any = None,
        candidate_mitigations: Optional[List[str]] = None,
        scope: Optional[Dict[str, Any]] = None,
    ) -> PredictedRisk:
        return cls.evaluate_risk(
            subject=subject,
            event=event,
            likelihood=likelihood,
            impact=impact,
            timeframe=timeframe,
            confidence=confidence,
            evidence=evidence,
            candidate_mitigations=candidate_mitigations,
            scope=scope,
        )
