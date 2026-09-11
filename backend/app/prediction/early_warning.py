"""Early Warning Engine with Hysteresis, Deduplication, and Attention Integration (Task 74, Spec 24-28, 65, 66, 68).

Key Invariants:
- EARLY WARNING != INCIDENT (Spec 24).
- Anti-Flapping Hysteresis: Activation threshold > Deactivation threshold (Spec 26).
- Alert Deduplication: Stable fingerprinting prevents duplicate alert storms (Spec 27).
- Fatigue Control: Routes into Attention Engine rather than bypassing it (Spec 28).
- Lead-Time Tracking: Measures warning lead time before event occurrence (Spec 68).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
import hashlib
import json
import logging
from typing import Any, Dict, List, Optional
import uuid

from app.prediction.schemas import (
    EarlyWarningResolution,
    EarlyWarningSeverity,
    EarlyWarningState,
)

logger = logging.getLogger("kairo.prediction.early_warning")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


# Backward-compatible enum aliases for Task 47
class WarningStatus(str, Enum):
    OPEN = "OPEN"
    WATCHING = "WATCHING"
    CONFIRMED = "CONFIRMED"
    DISMISSED = "DISMISSED"
    EXPIRED = "EXPIRED"
    RESOLVED = "RESOLVED"


class WarningSeverity(str, Enum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class EarlyWarningHysteresisConfig:
    """Anti-flapping hysteresis parameters (Spec 26)."""

    activation_threshold: float = 0.75
    deactivation_threshold: float = 0.60
    cooldown_seconds: int = 300
    min_persistence_seconds: int = 60


@dataclass
class EarlyWarning:
    """Proactive early warning with full lifecycle, hysteresis, and lead-time tracking (Spec 24-28)."""

    target: str
    signal: str
    predicted_event: str
    timeframe: Any
    confidence: float
    severity: Any = WarningSeverity.INFO
    evidence: Any = field(default_factory=list)
    status: Any = WarningStatus.OPEN
    warning_id: str = field(default_factory=lambda: f"ew_{uuid.uuid4().hex[:8]}")
    created_at: datetime = field(default_factory=utc_now)
    expires_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    escalation_count: int = 0
    scope: Dict[str, Any] = field(default_factory=dict)

    # Task 74 Extensions
    state: EarlyWarningState = EarlyWarningState.CREATED
    resolution: Optional[EarlyWarningResolution] = None
    fingerprint: str = ""
    hysteresis_active: bool = False
    last_state_change: datetime = field(default_factory=utc_now)
    lead_time_seconds: Optional[float] = None
    linked_forecast_ids: List[str] = field(default_factory=list)
    leading_indicators: List[str] = field(default_factory=list)
    recommended_investigation: str = ""

    def __post_init__(self) -> None:
        if self.expires_at is None:
            self.expires_at = self.created_at + timedelta(hours=4)
        if isinstance(self.evidence, list):
            self.evidence = list(self.evidence)
        elif isinstance(self.evidence, dict):
            self.evidence = dict(self.evidence)

        # Generate stable deduplication fingerprint if not set
        if not self.fingerprint:
            scope_str = json.dumps(self.scope, sort_keys=True)
            raw = f"{self.target}::{self.signal}::{self.predicted_event}::{scope_str}"
            self.fingerprint = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

        if self.state == EarlyWarningState.CREATED:
            self.state = EarlyWarningState.ACTIVE

    def is_expired(self) -> bool:
        """Check if warning relevance window has lapsed (Spec 38)."""
        return utc_now() > self.expires_at if self.expires_at else False

    def escalate(
        self,
        new_severity: Any,
        new_evidence: Any = None,
        confidence_boost: float = 0.1,
    ) -> None:
        """Escalate when evidence strengthens (Spec 27, 36)."""
        self.severity = new_severity
        if new_evidence:
            if isinstance(self.evidence, list):
                if isinstance(new_evidence, list):
                    self.evidence.extend(new_evidence)
                else:
                    self.evidence.append(new_evidence)
            elif isinstance(self.evidence, dict) and isinstance(new_evidence, dict):
                self.evidence.update(new_evidence)
        self.confidence = min(1.0, round(self.confidence + confidence_boost, 4))
        self.escalation_count += 1
        self.state = EarlyWarningState.ESCALATED
        self.last_state_change = utc_now()
        logger.warning(
            "Escalated warning %s on '%s' to %s (conf=%.2f)",
            self.warning_id,
            self.target,
            getattr(self.severity, "value", str(self.severity)),
            self.confidence,
        )

    def de_escalate(self, new_severity: Any, reason: str = "") -> None:
        """De-escalate warning when risk indicators recede below threshold."""
        self.severity = new_severity
        self.state = EarlyWarningState.DE_ESCALATED
        self.last_state_change = utc_now()
        logger.info("De-escalated warning %s on '%s' to %s: %s", self.warning_id, self.target, getattr(self.severity, "value", str(self.severity)), reason)

    def decay(self, factor: float = 0.8) -> None:
        """Reduce relevance as prediction window passes without event."""
        self.confidence = max(0.0, round(self.confidence * factor, 4))

    def resolve(
        self,
        resolution: EarlyWarningResolution,
        event_time: Optional[datetime] = None,
        details: Optional[str] = None,
    ) -> None:
        """Resolve warning with explicit reason and calculate lead time (Spec 66, 68)."""
        now = utc_now()
        self.resolved_at = now
        self.resolution = resolution
        self.state = EarlyWarningState.RESOLVED
        self.status = WarningStatus.RESOLVED

        if event_time is not None and resolution == EarlyWarningResolution.EVENT_OCCURRED:
            self.lead_time_seconds = max(0.0, (event_time - self.created_at).total_seconds())

        if details:
            if isinstance(self.evidence, list):
                self.evidence.append(f"Resolution details: {details}")

        logger.info(
            "Resolved early warning %s (%s): resolution=%s, lead_time=%.1fs",
            self.warning_id,
            self.target,
            resolution.value,
            self.lead_time_seconds or 0.0,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "warning_id": self.warning_id,
            "target": self.target,
            "signal": self.signal,
            "predicted_event": self.predicted_event,
            "timeframe": self.timeframe.value if hasattr(self.timeframe, "value") else str(self.timeframe),
            "confidence": round(self.confidence, 4),
            "severity": self.severity.value if hasattr(self.severity, "value") else str(self.severity),
            "status": self.status.value if hasattr(self.status, "value") else str(self.status),
            "state": self.state.value if hasattr(self.state, "value") else str(self.state),
            "resolution": self.resolution.value if self.resolution else None,
            "fingerprint": self.fingerprint,
            "evidence": self.evidence,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "is_expired": self.is_expired(),
            "escalation_count": self.escalation_count,
            "hysteresis_active": self.hysteresis_active,
            "lead_time_seconds": self.lead_time_seconds,
            "linked_forecast_ids": self.linked_forecast_ids,
            "leading_indicators": self.leading_indicators,
            "recommended_investigation": self.recommended_investigation,
            "scope": self.scope,
        }

    def to_attention_candidate_dict(self) -> Dict[str, Any]:
        """Convert early warning to structured payload for Attention Engine (Spec 28)."""
        sev_str = self.severity.value if hasattr(self.severity, "value") else str(self.severity)
        sev_map = {
            "CRITICAL": "CRITICAL",
            "WARNING": "HIGH",
            "HIGH": "HIGH",
            "ADVISORY": "MEDIUM",
            "MEDIUM": "MEDIUM",
            "WATCH": "LOW",
            "LOW": "LOW",
            "INFO": "LOW",
            "NORMAL": "LOW",
        }
        mapped_sev = sev_map.get(sev_str.upper(), "MEDIUM")

        urgency_val = 0.9 if mapped_sev == "CRITICAL" else (0.75 if mapped_sev == "HIGH" else 0.5)

        return {
            "source_type": "early_warning",
            "source_id": self.warning_id,
            "title": f"Early Warning: {self.predicted_event} on {self.target}",
            "description": f"Anticipated event '{self.predicted_event}' driven by signal '{self.signal}' with {self.confidence:.0%} confidence.",
            "importance": round(self.confidence, 3),
            "urgency": urgency_val,
            "severity": mapped_sev,
            "risk": round(self.confidence * (1.0 if mapped_sev == "CRITICAL" else 0.7), 3),
            "relevance": 0.85,
            "novelty": 0.5,
            "uncertainty": round(1.0 - self.confidence, 3),
            "provenance": {
                "fingerprint": self.fingerprint,
                "evidence_count": len(self.evidence) if isinstance(self.evidence, list) else 1,
                "created_at": self.created_at.isoformat(),
                "linked_forecast_ids": self.linked_forecast_ids,
            },
        }


class EarlyWarningManager:
    """Manages proactive early warning lifecycle with hysteresis, deduplication, and attention gating (Spec 24-28)."""

    def __init__(self, hysteresis_config: Optional[EarlyWarningHysteresisConfig] = None) -> None:
        self.hysteresis = hysteresis_config or EarlyWarningHysteresisConfig()
        self._warnings: Dict[str, EarlyWarning] = {}
        self._fingerprint_index: Dict[str, str] = {}
        self.false_positives_count: int = 0
        self.missed_warnings_count: int = 0
        self.verified_confirmations_count: int = 0

    def process_signal_with_hysteresis(
        self,
        target: str,
        signal: str,
        predicted_event: str,
        risk_score: float,
        evidence: Any = None,
        linked_forecast_ids: Optional[List[str]] = None,
        leading_indicators: Optional[List[str]] = None,
        scope: Optional[Dict[str, Any]] = None,
    ) -> Optional[EarlyWarning]:
        """Evaluates telemetry against activation/deactivation hysteresis thresholds (Spec 26)."""
        raw_key = f"{target}::{signal}::{predicted_event}::{json.dumps(scope or {}, sort_keys=True)}"
        fingerprint = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()[:16]
        existing_id = self._fingerprint_index.get(fingerprint)
        existing = self._warnings.get(existing_id) if existing_id else None

        now = utc_now()

        # 1. Existing warning active: check deactivation hysteresis
        if existing and existing.state in [EarlyWarningState.ACTIVE, EarlyWarningState.ESCALATED, EarlyWarningState.ACKNOWLEDGED]:
            if risk_score <= self.hysteresis.deactivation_threshold:
                # Check persistence/cooldown
                duration = (now - existing.last_state_change).total_seconds()
                if duration >= self.hysteresis.min_persistence_seconds:
                    existing.resolve(
                        resolution=EarlyWarningResolution.RISK_DECREASED,
                        details=f"Risk score decreased to {risk_score:.2f} (below deactivation threshold {self.hysteresis.deactivation_threshold:.2f})",
                    )
                    existing.hysteresis_active = False
                    return existing
            elif risk_score >= 0.85 and existing.confidence < risk_score:
                # Escalate
                existing.escalate(
                    new_severity=EarlyWarningSeverity.CRITICAL,
                    new_evidence=evidence,
                    confidence_boost=0.05,
                )
                return existing
            else:
                # Maintain active with hysteresis lock
                existing.hysteresis_active = True
                return existing

        # 2. Inactive or new: check activation threshold
        if risk_score >= self.hysteresis.activation_threshold:
            # Check cooldown from previous resolution
            if existing and existing.resolved_at:
                elapsed = (now - existing.resolved_at).total_seconds()
                if elapsed < self.hysteresis.cooldown_seconds:
                    logger.info("Early warning '%s' in cooldown period (%ds remaining); suppressed", target, self.hysteresis.cooldown_seconds - elapsed)
                    return None

            sev = EarlyWarningSeverity.CRITICAL if risk_score >= 0.85 else EarlyWarningSeverity.WARNING
            warning = self.create_warning(
                target=target,
                signal=signal,
                predicted_event=predicted_event,
                confidence=risk_score,
                severity=sev,
                evidence=evidence,
                linked_forecast_ids=linked_forecast_ids,
                leading_indicators=leading_indicators,
                scope=scope,
            )
            warning.hysteresis_active = True
            return warning

        return None

    def create_warning(
        self,
        target: str,
        signal: str,
        predicted_event: str,
        confidence: float,
        timeframe: Any = "short-term",
        severity: Any = WarningSeverity.INFO,
        evidence: Any = None,
        duration_hours: float = 4.0,
        scope: Optional[Dict[str, Any]] = None,
        linked_forecast_ids: Optional[List[str]] = None,
        leading_indicators: Optional[List[str]] = None,
        recommended_investigation: Optional[str] = None,
    ) -> EarlyWarning:
        """Create or update-in-place early warning using stable fingerprinting (Spec 27)."""
        raw_key = f"{target}::{signal}::{predicted_event}::{json.dumps(scope or {}, sort_keys=True)}"
        fingerprint = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()[:16]

        existing_id = self._fingerprint_index.get(fingerprint)
        if existing_id and existing_id in self._warnings:
            existing = self._warnings[existing_id]
            if not existing.is_expired() and existing.state in [
                EarlyWarningState.ACTIVE,
                EarlyWarningState.ACKNOWLEDGED,
                EarlyWarningState.ESCALATED,
            ]:
                # Combine / update in place rather than flood duplicates
                if confidence > existing.confidence:
                    existing.confidence = confidence
                if severity:
                    existing.severity = severity
                if evidence:
                    if isinstance(existing.evidence, list):
                        if isinstance(evidence, list):
                            for e in evidence:
                                if e not in existing.evidence:
                                    existing.evidence.append(e)
                        elif evidence not in existing.evidence:
                            existing.evidence.append(evidence)
                if linked_forecast_ids:
                    for f in linked_forecast_ids:
                        if f not in existing.linked_forecast_ids:
                            existing.linked_forecast_ids.append(f)
                return existing

        wid = f"ew_{uuid.uuid4().hex[:8]}"
        warning = EarlyWarning(
            warning_id=wid,
            target=target,
            signal=signal,
            predicted_event=predicted_event,
            timeframe=timeframe,
            confidence=max(0.0, min(1.0, confidence)),
            severity=severity,
            evidence=evidence or [],
            expires_at=utc_now() + timedelta(hours=duration_hours),
            scope=scope or {},
            fingerprint=fingerprint,
            linked_forecast_ids=linked_forecast_ids or [],
            leading_indicators=leading_indicators or [],
            recommended_investigation=recommended_investigation or f"Inspect telemetry on {target}",
        )

        self._warnings[wid] = warning
        self._fingerprint_index[fingerprint] = wid
        logger.info(
            "Issued early warning %s on '%s' (sev=%s, conf=%.2f, fp=%s)",
            wid,
            target,
            getattr(severity, "value", str(severity)),
            confidence,
            fingerprint,
        )
        return warning

    def issue_warning(
        self,
        target: str,
        signal: str,
        predicted_event: str,
        confidence: float,
        timeframe: Any = "short-term",
        severity: Any = WarningSeverity.INFO,
        evidence: Any = None,
        duration_hours: float = 4.0,
        scope: Optional[Dict[str, Any]] = None,
    ) -> EarlyWarning:
        """Alias for backward compatibility with Task 47."""
        return self.create_warning(
            target=target,
            signal=signal,
            predicted_event=predicted_event,
            confidence=confidence,
            timeframe=timeframe,
            severity=severity,
            evidence=evidence,
            duration_hours=duration_hours,
            scope=scope,
        )

    def acknowledge_warning(self, warning_id: str, actor: str = "user") -> EarlyWarning:
        """Mark warning as acknowledged by operator (Spec 65)."""
        w = self._warnings.get(warning_id)
        if not w:
            raise KeyError(f"Early warning '{warning_id}' not found.")
        w.state = EarlyWarningState.ACKNOWLEDGED
        w.last_state_change = utc_now()
        w.scope["acknowledged_by"] = actor
        return w

    def dismiss_warning(self, warning_id: str, reason: str = "Operator dismissed") -> EarlyWarning:
        """Manually dismiss warning as non-actionable (Spec 65, 66)."""
        w = self._warnings.get(warning_id)
        if not w:
            raise KeyError(f"Early warning '{warning_id}' not found.")
        w.resolve(resolution=EarlyWarningResolution.MANUALLY_DISMISSED, details=reason)
        return w

    def escalate_warning(
        self,
        warning_id: str,
        new_confidence: float,
        new_severity: Any,
        new_evidence: Any = None,
    ) -> EarlyWarning:
        w = self._warnings.get(warning_id)
        if not w:
            raise KeyError(f"Warning {warning_id} not found")
        w.escalate(new_severity=new_severity, new_evidence=new_evidence, confidence_boost=max(0.0, new_confidence - w.confidence))
        return w

    def decay_warning(self, warning_id: str, decay_factor: float = 0.8) -> EarlyWarning:
        w = self._warnings.get(warning_id)
        if not w:
            raise KeyError(f"Warning {warning_id} not found")
        w.decay(decay_factor)
        return w

    def confirm_warning(self, warning_id: str, evidence_details: Optional[str] = None) -> EarlyWarning:
        """Enforce confirmed transition when actual outcome is observed (Spec 65, 66, 68)."""
        w = self._warnings.get(warning_id)
        if not w:
            raise KeyError(f"Warning {warning_id} not found")
        w.resolve(
            resolution=EarlyWarningResolution.EVENT_OCCURRED,
            event_time=utc_now(),
            details=evidence_details,
        )
        w.status = WarningStatus.CONFIRMED
        self.verified_confirmations_count += 1
        return w

    def expire_stale_warnings(self) -> int:
        """Enforce Spec 38: Expire warnings after window ends."""
        expired = 0
        now = utc_now()
        for w in self._warnings.values():
            if w.state in [EarlyWarningState.ACTIVE, EarlyWarningState.ACKNOWLEDGED] and w.expires_at and now > w.expires_at:
                w.state = EarlyWarningState.EXPIRED
                w.status = WarningStatus.EXPIRED
                w.resolution = EarlyWarningResolution.FORECAST_EXPIRED
                expired += 1
        return expired

    def record_outcome(self, warning_id: str, actual_occurred: bool) -> None:
        """Enforce Spec 39, 40: Track false positives and verified confirmations."""
        w = self._warnings.get(warning_id)
        if not w:
            return
        if actual_occurred:
            w.resolve(resolution=EarlyWarningResolution.EVENT_OCCURRED, event_time=utc_now())
            self.verified_confirmations_count += 1
        else:
            w.resolve(resolution=EarlyWarningResolution.FALSE_POSITIVE)
            self.false_positives_count += 1
            logger.info("Recorded false positive early warning on '%s'", w.target)

    def get_warning(self, warning_id: str) -> Optional[EarlyWarning]:
        return self._warnings.get(warning_id)

    def get_active_warnings(self) -> List[EarlyWarning]:
        self.expire_stale_warnings()
        return [
            w for w in self._warnings.values()
            if w.state in [EarlyWarningState.ACTIVE, EarlyWarningState.ACKNOWLEDGED, EarlyWarningState.ESCALATED]
        ]

    def list_all(self) -> List[EarlyWarning]:
        return list(self._warnings.values())


early_warning_manager = EarlyWarningManager()
