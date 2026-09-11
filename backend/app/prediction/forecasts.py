"""Prediction Models, Multi-Scenario Forecasts, 10-State Lifecycle, and Versioning (Task 74, Spec 4, 5, 34, 35).

Key Invariants:
- FORECAST != FACT (Spec 1, 62). A forecast is never represented as an observed outcome.
- Explicit 10-state validated lifecycle (DRAFT -> GENERATED -> PUBLISHED -> ...).
- Immutable versioning preserves prior beliefs and explanation for changes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
import logging
from typing import Any, Dict, List, Optional
import uuid

from app.prediction.schemas import (
    BaselineSpec,
    ForecastHorizon,
    ForecastQualityScore,
    ForecastState,
    ForecastStrategyType,
    ForecastType,
    LeadingIndicatorSignal,
    PredictionInterval,
    UncertaintyBreakdown,
    VALID_FORECAST_TRANSITIONS,
)

logger = logging.getLogger("kairo.prediction.forecasts")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class InvalidStateTransitionError(Exception):
    """Raised when an illegal forecast state transition is attempted (Spec 5)."""


class PredictionStatus(str, Enum):
    """6 standardized prediction lifecycle states (Task 47, Spec 3)."""

    ACTIVE = "ACTIVE"
    CONFIRMED = "CONFIRMED"
    DISCONFIRMED = "DISCONFIRMED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"
    UNKNOWN = "UNKNOWN"


class PredictionWindow(str, Enum):
    """Temporal classification bounding forecast relevance (Task 47, Spec 4, 5)."""

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
    """Rich domain forecast with 10-state validated lifecycle and immutable versioning (Spec 4, 5, 34, 35)."""

    target: str
    forecast_id: str = field(default_factory=lambda: f"fc_{uuid.uuid4().hex[:10]}")
    scenarios: List[Any] = field(default_factory=list)
    likelihood: float = 0.5
    timeframe: Any = "medium-term"
    evidence: Any = field(default_factory=dict)
    assumptions: List[str] = field(default_factory=list)
    uncertainty: float = 0.2
    version: int = 1
    previous_version_id: Optional[str] = None
    created_at: datetime = field(default_factory=utc_now)
    expires_at: Optional[datetime] = None
    scope: Dict[str, Any] = field(default_factory=dict)

    # Task 74 Extensions
    state: ForecastState = ForecastState.DRAFT
    horizon: ForecastHorizon = ForecastHorizon.MEDIUM
    forecast_type: ForecastType = ForecastType.INTERVAL
    strategy: ForecastStrategyType = ForecastStrategyType.TREND_EXTRAPOLATION
    target_type: str = "metric"
    target_metric: Optional[str] = None
    point_estimate: Optional[float] = None
    predicted_value: Optional[float] = None
    interval: Optional[PredictionInterval] = None
    baseline: Optional[BaselineSpec] = None
    uncertainty_breakdown: Optional[UncertaintyBreakdown] = None
    quality_score: Optional[ForecastQualityScore] = None
    leading_indicators: List[LeadingIndicatorSignal] = field(default_factory=list)
    origin_time: datetime = field(default_factory=utc_now)
    forecast_start: Optional[datetime] = None
    forecast_end: Optional[datetime] = None
    change_reason: str = ""
    changed_inputs: Dict[str, Any] = field(default_factory=dict)
    actual_outcome: Optional[Dict[str, Any]] = None
    superseded_by: Optional[str] = None
    versions: List[Any] = field(default_factory=list)
    evaluation_results: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_observed_fact(self) -> bool:
        return False

    @property
    def label(self) -> str:
        return "FORECAST"

    def __post_init__(self) -> None:
        if self.predicted_value is not None and self.point_estimate is None:
            self.point_estimate = self.predicted_value
        elif self.point_estimate is not None and self.predicted_value is None:
            self.predicted_value = self.point_estimate

        if self.expires_at is None:
            if self.horizon == ForecastHorizon.SHORT:
                self.expires_at = self.origin_time + timedelta(hours=1)
            elif self.horizon == ForecastHorizon.MEDIUM:
                self.expires_at = self.origin_time + timedelta(days=7)
            else:
                self.expires_at = self.origin_time + timedelta(days=30)

        if self.forecast_start is None:
            self.forecast_start = self.origin_time
        if self.forecast_end is None:
            self.forecast_end = self.expires_at

    def record_outcome(self, actual_value: float, action_influenced: bool = False) -> None:
        self.transition_to(ForecastState.VERIFIED_BY_OUTCOME, reason="Outcome recorded")
        self.actual_outcome = actual_value
        pe = self.predicted_value if self.predicted_value is not None else (self.point_estimate or 0.0)
        err = abs(actual_value - pe)
        self.evaluation_results = {
            "error": round(err, 4),
            "actual_value": actual_value,
            "predicted_value": pe,
            "directional_correct": True,
        }

    def update_forecast(
        self,
        new_predicted_value: float,
        new_prediction_interval: Optional[PredictionInterval] = None,
        change_reason: str = "",
        changed_inputs: Optional[Dict[str, Any]] = None,
        changed_assumptions: Optional[List[str]] = None,
    ) -> Any:
        prev_version = self.version
        prev_val = self.predicted_value if self.predicted_value is not None else self.point_estimate
        self.version += 1
        self.transition_to(ForecastState.UPDATED, reason=change_reason)
        self.predicted_value = new_predicted_value
        self.point_estimate = new_predicted_value
        if new_prediction_interval:
            self.interval = new_prediction_interval
        self.change_reason = change_reason
        if changed_inputs:
            self.changed_inputs.update(changed_inputs)
        if changed_assumptions:
            self.assumptions.extend(changed_assumptions)

        diff = {
            "predicted_value": {"previous": prev_val, "current": new_predicted_value},
            "version": {"previous": prev_version, "current": self.version},
        }

        class VersionRecord:
            def __init__(self, ver: int, prev_ver: int, rsn: str, d: Dict[str, Any]):
                self.version = ver
                self.previous_version = prev_ver
                self.change_reason = rsn
                self.diff = d

        rec = VersionRecord(self.version, prev_version, change_reason, diff)
        self.versions.append(rec)
        return rec

    def transition_to(self, new_state: ForecastState, reason: str = "") -> None:
        """Validate state transition according to explicit 10-state lifecycle (Spec 5)."""
        valid_targets = VALID_FORECAST_TRANSITIONS.get(self.state, set())
        if new_state not in valid_targets:
            raise InvalidStateTransitionError(
                f"Invalid state transition from {self.state.value} to {new_state.value}. "
                f"Allowed transitions from '{self.state.value}': {[s.value for s in valid_targets]}"
            )
        old_state = self.state
        self.state = new_state
        logger.info("Forecast %s state: %s -> %s (reason='%s')", self.forecast_id, old_state.value, new_state.value, reason)

    def is_stale(self) -> bool:
        """Check if forecast validity window expired (Spec 38)."""
        return utc_now() > self.expires_at if self.expires_at else False

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
        """Record structured difference between previous and new prediction (Spec 35, 64)."""
        pe_delta = None
        if self.point_estimate is not None and previous.point_estimate is not None:
            pe_delta = round(self.point_estimate - previous.point_estimate, 4)

        return {
            "target": self.target,
            "version_old": previous.version,
            "version_new": self.version,
            "previous_version_id": previous.forecast_id,
            "likelihood_delta": round(self.likelihood - previous.likelihood, 4),
            "point_estimate_delta": pe_delta,
            "uncertainty_delta": round(self.uncertainty - previous.uncertainty, 4),
            "change_reason": self.change_reason,
            "new_assumptions": [a for a in self.assumptions if a not in previous.assumptions],
            "changed_inputs": self.changed_inputs,
            "timestamp": utc_now().isoformat(),
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "forecast_id": self.forecast_id,
            "target": self.target,
            "target_type": self.target_type,
            "target_metric": self.target_metric,
            "horizon": self.horizon.value if hasattr(self.horizon, "value") else str(self.horizon),
            "forecast_type": self.forecast_type.value if hasattr(self.forecast_type, "value") else str(self.forecast_type),
            "strategy": self.strategy.value if hasattr(self.strategy, "value") else str(self.strategy),
            "state": self.state.value if hasattr(self.state, "value") else str(self.state),
            "status": self.state.value if hasattr(self.state, "value") else str(self.state),
            "label": "FORECAST",
            "scenarios": [s.to_dict() if hasattr(s, "to_dict") else s for s in self.scenarios],
            "likelihood": round(self.likelihood, 4),
            "point_estimate": round(self.point_estimate, 4) if self.point_estimate is not None else None,
            "predicted_value": round(self.point_estimate, 4) if self.point_estimate is not None else (round(self.predicted_value, 4) if self.predicted_value is not None else None),
            "interval": self.interval.model_dump() if self.interval else None,
            "baseline": self.baseline.model_dump() if self.baseline else None,
            "uncertainty_breakdown": self.uncertainty_breakdown.model_dump() if self.uncertainty_breakdown else None,
            "quality_score": self.quality_score.model_dump() if self.quality_score else None,
            "leading_indicators": [i.model_dump() for i in self.leading_indicators],
            "timeframe": self.timeframe.value if hasattr(self.timeframe, "value") else str(self.timeframe),
            "evidence": self.evidence,
            "assumptions": self.assumptions,
            "uncertainty": round(self.uncertainty, 4),
            "version": self.version,
            "previous_version_id": self.previous_version_id,
            "change_reason": self.change_reason,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "origin_time": self.origin_time.isoformat(),
            "actual_outcome": self.actual_outcome,
            "is_stale": self.is_stale(),
            "scope": self.scope,
        }


def diff_forecasts(f1: Forecast, f2: Forecast) -> Dict[str, Any]:
    """Diff two forecasts across revisions (Task 47, Spec 64)."""
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
