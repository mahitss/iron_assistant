"""Prediction Models, Multi-Scenario Forecasts, Time Windows, and Revision History (Task 47)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
import logging
from typing import Any, Dict, List, Optional
import uuid

logger = logging.getLogger("kairo.prediction.forecasts")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class PredictionStatus(str, Enum):
    """6 standardized prediction lifecycle states (Spec 3)."""

    ACTIVE = "ACTIVE"
    CONFIRMED = "CONFIRMED"
    DISCONFIRMED = "DISCONFIRMED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"
    UNKNOWN = "UNKNOWN"


class PredictionWindow(str, Enum):
    """Temporal classification bounding forecast relevance (Spec 4, 5)."""

    NEAR_TERM = "near-term"      # 0 to 1 hour
    SHORT_TERM = "short-term"    # 1 to 24 hours
    MEDIUM_TERM = "medium-term"  # 1 to 7 days
    LONG_TERM = "long-term"      # > 7 days
    EXPLICIT = "explicit"        # Explicit time interval


@dataclass
class Prediction:
    """Bounded, time-versioned environmental state prediction (Spec 2-5)."""

    subject: str
    event: str
    predicted_state: Dict[str, Any]
    prediction_window: PredictionWindow
    confidence: float
    model_reference: str = "default_forecaster"
    prediction_id: str = field(default_factory=lambda: f"pred_{uuid.uuid4().hex[:10]}")
    created_at: datetime = field(default_factory=utc_now)
    expires_at: Optional[datetime] = None
    assumptions: List[str] = field(default_factory=list)
    evidence_refs: List[str] = field(default_factory=list)
    status: PredictionStatus = PredictionStatus.ACTIVE
    scope: Dict[str, Any] = field(default_factory=dict)
    actual_outcome: Optional[Dict[str, Any]] = None
    action_influenced: bool = False  # Enforce Spec 24: Kairo actions must not create self-fulfilling natural labels
    resolved_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        if self.expires_at is None:
            if self.prediction_window == PredictionWindow.NEAR_TERM:
                self.expires_at = self.created_at + timedelta(hours=1)
            elif self.prediction_window == PredictionWindow.SHORT_TERM:
                self.expires_at = self.created_at + timedelta(hours=24)
            elif self.prediction_window == PredictionWindow.MEDIUM_TERM:
                self.expires_at = self.created_at + timedelta(days=7)
            elif self.prediction_window == PredictionWindow.LONG_TERM:
                self.expires_at = self.created_at + timedelta(days=30)
            else:
                self.expires_at = self.created_at + timedelta(hours=4)

    @property
    def is_expired(self) -> bool:
        """Check if temporal prediction window has lapsed (Spec 38, 144)."""
        return utc_now() > self.expires_at if self.expires_at else False

    def confirm(self, evidence: Optional[List[str]] = None) -> None:
        self.status = PredictionStatus.CONFIRMED
        self.resolved_at = utc_now()
        if evidence:
            for e in evidence:
                if e not in self.evidence_refs:
                    self.evidence_refs.append(e)

    def disconfirm(self, reason: Optional[str] = None) -> None:
        self.status = PredictionStatus.DISCONFIRMED
        self.resolved_at = utc_now()
        if reason:
            self.assumptions.append(reason)

    def evaluate_outcome(self, actual_state: Dict[str, Any], was_action_influenced: bool = False) -> PredictionStatus:
        """Enforce Spec 138-143: Update status based on verified empirical outcome."""
        self.actual_outcome = actual_state
        self.action_influenced = was_action_influenced
        self.resolved_at = utc_now()

        # Compare predicted state vs actual state
        matches = all(actual_state.get(k) == v for k, v in self.predicted_state.items())
        if matches:
            self.status = PredictionStatus.CONFIRMED
        else:
            self.status = PredictionStatus.DISCONFIRMED

        logger.info(
            "Evaluated prediction %s on '%s': status=%s (action_influenced=%s)",
            self.prediction_id,
            self.subject,
            self.status.value,
            was_action_influenced,
        )
        return self.status

    def to_dict(self) -> Dict[str, Any]:
        return {
            "prediction_id": self.prediction_id,
            "subject": self.subject,
            "event": self.event,
            "predicted_state": self.predicted_state,
            "prediction_window": self.prediction_window.value if hasattr(self.prediction_window, "value") else str(self.prediction_window),
            "confidence": round(self.confidence, 4),
            "model_reference": self.model_reference,
            "assumptions": self.assumptions,
            "evidence_refs": self.evidence_refs,
            "status": self.status.value if hasattr(self.status, "value") else str(self.status),
            "scope": self.scope,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "is_expired": self.is_expired,
            "actual_outcome": self.actual_outcome,
            "action_influenced": self.action_influenced,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
        }


@dataclass
class Forecast:
    """Multi-scenario future projection maintaining versioning and diffs (Spec 6-11, 63, 64)."""

    target: str
    forecast_id: str = field(default_factory=lambda: f"fc_{uuid.uuid4().hex[:10]}")
    scenarios: List[Any] = field(default_factory=list)
    likelihood: float = 0.5
    timeframe: Any = "medium-term"
    evidence: Any = field(default_factory=list)
    assumptions: List[str] = field(default_factory=list)
    uncertainty: float = 0.2
    version: int = 1
    previous_version_id: Optional[str] = None
    created_at: datetime = field(default_factory=utc_now)
    scope: Dict[str, Any] = field(default_factory=dict)

    @property
    def baseline_scenario(self) -> Optional[Any]:
        for s in self.scenarios:
            if getattr(s, "is_baseline", False) or (isinstance(s, dict) and s.get("is_baseline")):
                return s
        return self.scenarios[0] if self.scenarios else None

    @property
    def intervention_scenarios(self) -> List[Any]:
        return [
            s for s in self.scenarios
            if not getattr(s, "is_baseline", False) and not (isinstance(s, dict) and s.get("is_baseline"))
        ]

    def diff_from_previous(self, previous: Forecast) -> Dict[str, Any]:
        """Enforce Spec 64: Record diff between previous and new prediction."""
        return {
            "target": self.target,
            "version_old": previous.version,
            "version_new": self.version,
            "likelihood_delta": round(self.likelihood - previous.likelihood, 4),
            "uncertainty_delta": round(self.uncertainty - previous.uncertainty, 4),
            "new_assumptions": [a for a in self.assumptions if a not in previous.assumptions],
            "timestamp": utc_now().isoformat(),
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "forecast_id": self.forecast_id,
            "target": self.target,
            "scenarios": [s.to_dict() if hasattr(s, "to_dict") else s for s in self.scenarios],
            "likelihood": round(self.likelihood, 4),
            "timeframe": self.timeframe.value if hasattr(self.timeframe, "value") else str(self.timeframe),
            "evidence": self.evidence,
            "assumptions": self.assumptions,
            "uncertainty": round(self.uncertainty, 4),
            "version": self.version,
            "previous_version_id": self.previous_version_id,
            "created_at": self.created_at.isoformat(),
            "scope": self.scope,
        }


def diff_forecasts(f1: Forecast, f2: Forecast) -> Dict[str, Any]:
    """Diff two forecasts across revisions (Spec 64)."""
    ev1 = f1.evidence if isinstance(f1.evidence, list) else list(f1.evidence.keys()) if isinstance(f1.evidence, dict) else []
    ev2 = f2.evidence if isinstance(f2.evidence, list) else list(f2.evidence.keys()) if isinstance(f2.evidence, dict) else []
    new_ev = [e for e in ev2 if e not in ev1]

    return {
        "target": f2.target,
        "old_version": f1.version,
        "new_version": f2.version,
        "likelihood_diff": round(f2.likelihood - f1.likelihood, 4),
        "new_evidence": new_ev,
        "scenario_count_diff": len(f2.scenarios) - len(f1.scenarios),
    }
