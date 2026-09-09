"""Early Warning System, Significance Classification, Alert Deduplication, and Expiration (Task 47)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
import logging
from typing import Any, Dict, List, Optional
import uuid

logger = logging.getLogger("kairo.prediction.early_warning")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class WarningStatus(str, Enum):
    """6 early warning operational lifecycle states (Spec 31)."""

    OPEN = "OPEN"
    WATCHING = "WATCHING"
    CONFIRMED = "CONFIRMED"
    DISMISSED = "DISMISSED"
    EXPIRED = "EXPIRED"
    RESOLVED = "RESOLVED"


class WarningSeverity(str, Enum):
    """5 standardized warning criticality levels (Spec 33)."""

    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class EarlyWarning:
    """Proactive early warning alerting to probable near-term issues (Spec 30-40)."""

    target: str
    signal: str
    predicted_event: str
    timeframe: Any
    confidence: float
    severity: WarningSeverity = WarningSeverity.INFO
    evidence: Any = field(default_factory=list)
    status: WarningStatus = WarningStatus.OPEN
    warning_id: str = field(default_factory=lambda: f"ew_{uuid.uuid4().hex[:8]}")
    created_at: datetime = field(default_factory=utc_now)
    expires_at: Optional[datetime] = None
    escalation_count: int = 0
    scope: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.expires_at is None:
            self.expires_at = self.created_at + timedelta(hours=4)
        if isinstance(self.evidence, list):
            self.evidence = list(self.evidence)
        elif isinstance(self.evidence, dict):
            self.evidence = dict(self.evidence)

    def is_expired(self) -> bool:
        """Check if warning relevance window has lapsed (Spec 38)."""
        return utc_now() > self.expires_at if self.expires_at else False

    def escalate(self, new_severity: WarningSeverity, new_evidence: Any = None, confidence_boost: float = 0.1) -> None:
        """Enforce Spec 36: Escalate when evidence strengthens."""
        self.severity = new_severity
        if new_evidence:
            if isinstance(self.evidence, list):
                if isinstance(new_evidence, list):
                    self.evidence.extend(new_evidence)
                else:
                    self.evidence.append(new_evidence)
            elif isinstance(self.evidence, dict) and isinstance(new_evidence, dict):
                self.evidence.update(new_evidence)
        self.confidence = min(1.0, self.confidence + confidence_boost)
        self.escalation_count += 1
        logger.warning("Escalated warning %s on %s to %s (conf=%.2f)", self.warning_id, self.target, self.severity.value, self.confidence)

    def decay(self, factor: float = 0.8) -> None:
        """Enforce Spec 37: Reduce relevance as prediction window passes."""
        self.confidence = max(0.0, round(self.confidence * factor, 4))

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
            "evidence": self.evidence,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "is_expired": self.is_expired(),
            "escalation_count": self.escalation_count,
            "scope": self.scope,
        }


class EarlyWarningManager:
    """Tracks, deduplicates, and manages early warning lifecycle without alert storms (Spec 30-40)."""

    def __init__(self) -> None:
        self._warnings: Dict[str, EarlyWarning] = {}
        self._dedup_index: Dict[str, str] = {}
        self.false_positives_count: int = 0
        self.missed_warnings_count: int = 0

    def create_warning(
        self,
        target: str,
        signal: str,
        predicted_event: str,
        confidence: float,
        timeframe: Any = "short-term",
        severity: WarningSeverity = WarningSeverity.INFO,
        evidence: Any = None,
        duration_hours: float = 4.0,
        scope: Optional[Dict[str, Any]] = None,
    ) -> EarlyWarning:
        """Create or deduplicate early warning (Spec 34, 35)."""
        dedup_key = f"{target}:{predicted_event}"
        existing_id = self._dedup_index.get(dedup_key)

        if existing_id and existing_id in self._warnings:
            existing = self._warnings[existing_id]
            if not existing.is_expired() and existing.status in [WarningStatus.OPEN, WarningStatus.WATCHING]:
                # Combine / escalate existing warning rather than duplicate (Spec 35, 36)
                if confidence > existing.confidence:
                    existing.confidence = confidence
                if severity and severity != existing.severity:
                    existing.severity = severity
                if evidence:
                    if isinstance(existing.evidence, list):
                        if isinstance(evidence, list):
                            for e in evidence:
                                if e not in existing.evidence:
                                    existing.evidence.append(e)
                        elif evidence not in existing.evidence:
                            existing.evidence.append(evidence)
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
        )
        self._warnings[wid] = warning
        self._dedup_index[dedup_key] = wid
        logger.info("Issued early warning %s on %s (sev=%s, conf=%.2f)", wid, target, severity.value, confidence)
        return warning

    def issue_warning(
        self,
        target: str,
        signal: str,
        predicted_event: str,
        confidence: float,
        timeframe: Any = "short-term",
        severity: WarningSeverity = WarningSeverity.INFO,
        evidence: Any = None,
        duration_hours: float = 4.0,
        scope: Optional[Dict[str, Any]] = None,
    ) -> EarlyWarning:
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

    def escalate_warning(
        self,
        warning_id: str,
        new_confidence: float,
        new_severity: WarningSeverity,
        new_evidence: Any = None,
    ) -> EarlyWarning:
        w = self._warnings.get(warning_id)
        if not w:
            raise KeyError(f"Warning {warning_id} not found")
        w.severity = new_severity
        w.confidence = new_confidence
        if new_evidence:
            if isinstance(w.evidence, list):
                if isinstance(new_evidence, list):
                    w.evidence.extend(new_evidence)
                else:
                    w.evidence.append(new_evidence)
            elif isinstance(w.evidence, dict) and isinstance(new_evidence, dict):
                w.evidence.update(new_evidence)
        w.escalation_count += 1
        return w

    def decay_warning(self, warning_id: str, decay_factor: float = 0.8) -> EarlyWarning:
        w = self._warnings.get(warning_id)
        if not w:
            raise KeyError(f"Warning {warning_id} not found")
        w.decay(decay_factor)
        return w

    def confirm_warning(self, warning_id: str, evidence_details: Optional[str] = None) -> EarlyWarning:
        w = self._warnings.get(warning_id)
        if not w:
            raise KeyError(f"Warning {warning_id} not found")
        w.status = WarningStatus.CONFIRMED
        if evidence_details:
            if isinstance(w.evidence, list):
                w.evidence.append(evidence_details)
        return w

    def expire_stale_warnings(self) -> int:
        """Enforce Spec 38: Expire warnings after window ends."""
        expired = 0
        now = utc_now()
        for w in self._warnings.values():
            if w.status == WarningStatus.OPEN and w.expires_at and now > w.expires_at:
                w.status = WarningStatus.EXPIRED
                expired += 1
        return expired

    def record_outcome(self, warning_id: str, actual_occurred: bool) -> None:
        """Enforce Spec 39, 40: Track false positives and verified confirmations."""
        w = self._warnings.get(warning_id)
        if not w:
            return
        if actual_occurred:
            w.status = WarningStatus.CONFIRMED
        else:
            w.status = WarningStatus.DISMISSED
            self.false_positives_count += 1
            logger.info("Recorded false positive early warning on %s", w.target)

    def get_active_warnings(self) -> List[EarlyWarning]:
        self.expire_stale_warnings()
        return [w for w in self._warnings.values() if w.status in [WarningStatus.OPEN, WarningStatus.WATCHING]]
