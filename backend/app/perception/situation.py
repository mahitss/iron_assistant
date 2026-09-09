"""Situational Awareness Synthesis, Live Anomaly Detection, and Maintenance Context (Task 46)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
import uuid

from app.perception.changes import ChangeEvent
from app.perception.observations import Observation

logger = logging.getLogger("kairo.perception.situation")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class Anomaly:
    """Diagnostic signal flagging unexpected environmental deviations (Spec 89, 90)."""

    anomaly_id: str
    subject: str
    expected: Any
    observed: Any
    deviation: float
    confidence: float
    evidence: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=utc_now)
    is_suppressed_by_plan: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "anomaly_id": self.anomaly_id,
            "subject": self.subject,
            "expected": self.expected,
            "observed": self.observed,
            "deviation": self.deviation,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "timestamp": self.timestamp.isoformat(),
            "is_suppressed_by_plan": self.is_suppressed_by_plan,
        }


@dataclass
class Situation:
    """Synthesized environmental awareness representation for cognitive context (Spec 100-106)."""

    situation_id: str
    version: int
    scope: Dict[str, Any]
    summary: str  # Clearly distinguishes observed facts vs inferences (Spec 101, 102)
    observed_facts: List[str] = field(default_factory=list)
    inferences: List[str] = field(default_factory=list)
    changes: List[Dict[str, Any]] = field(default_factory=list)
    anomalies: List[Dict[str, Any]] = field(default_factory=list)
    active_tasks: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)
    uncertainties: List[str] = field(default_factory=list)  # Missing observations remain UNKNOWN (Spec 103)
    timestamp: datetime = field(default_factory=utc_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "situation_id": self.situation_id,
            "version": self.version,
            "scope": self.scope,
            "summary": self.summary,
            "observed_facts": self.observed_facts,
            "inferences": self.inferences,
            "changes": self.changes,
            "anomalies": self.anomalies,
            "active_tasks": self.active_tasks,
            "risks": self.risks,
            "uncertainties": self.uncertainties,
            "timestamp": self.timestamp.isoformat(),
        }


class SituationalAwarenessManager:
    """Synthesizes live situation summaries without fabricating unobserved facts (Spec 100-106)."""

    def __init__(self) -> None:
        self._current_version = 0
        self._history: List[Situation] = []
        # subject -> planned operation / maintenance window
        self._active_maintenance_windows: Dict[str, str] = {}

    def register_maintenance_window(self, subject: str, reason: str) -> None:
        """Register planned change window to avoid false anomaly alarms (Spec 93, 94)."""
        self._active_maintenance_windows[subject] = reason

    def detect_anomaly(
        self,
        subject: str,
        expected: Any,
        observed: Any,
        confidence: float = 1.0,
    ) -> Optional[Anomaly]:
        """Detect deviation while correlating with planned maintenance (Spec 89-95)."""
        if expected == observed:
            return None

        is_suppressed = subject in self._active_maintenance_windows
        anom_id = f"anom_{uuid.uuid4().hex[:8]}"

        anomaly = Anomaly(
            anomaly_id=anom_id,
            subject=subject,
            expected=expected,
            observed=observed,
            deviation=1.0,
            confidence=confidence,
            evidence={"maintenance_reason": self._active_maintenance_windows.get(subject)},
            is_suppressed_by_plan=is_suppressed,
        )
        if not is_suppressed:
            logger.warning("Environmental anomaly detected on '%s': expected %s, observed %s", subject, expected, observed)
        return anomaly

    def synthesize_situation(
        self,
        scope: Dict[str, Any],
        observations: List[Observation],
        changes: List[ChangeEvent],
        anomalies: List[Anomaly],
        active_tasks: Optional[List[str]] = None,
        unknown_sources: Optional[List[str]] = None,
    ) -> Situation:
        """Construct versioned situational awareness distinguishing fact from inference (Spec 101-106)."""
        self._current_version += 1
        sit_id = f"sit_v{self._current_version}_{uuid.uuid4().hex[:8]}"

        facts = [f"Observed '{o.subject}': {o.data}" for o in observations[:5]]
        change_records = [c.to_dict() for c in changes[:5]]
        anom_records = [a.to_dict() for a in anomalies if not a.is_suppressed_by_plan]

        risks = []
        for anom in anomalies:
            if not anom.is_suppressed_by_plan:
                risks.append(f"Unplanned deviation on {anom.subject}")
        for chg in changes:
            if chg.significance.value in ["HIGH", "CRITICAL"]:
                risks.append(f"{chg.significance.value} change on {chg.subject}")

        # Uncertainties for unobserved / missing sources (Spec 103)
        uncertainties = [f"Source '{s}' is offline/unavailable; state unknown" for s in (unknown_sources or [])]

        summary_parts = []
        if facts:
            summary_parts.append(f"{len(facts)} active verified telemetry facts")
        if risks:
            summary_parts.append(f"{len(risks)} identified risks")
        if uncertainties:
            summary_parts.append(f"{len(uncertainties)} unobserved uncertainties")

        summary = "; ".join(summary_parts) if summary_parts else "Environment quiescent; all authorized sources nominal."

        situation = Situation(
            situation_id=sit_id,
            version=self._current_version,
            scope=scope,
            summary=summary,
            observed_facts=facts,
            inferences=[f"Likely consequence: {r}" for r in risks],
            changes=change_records,
            anomalies=anom_records,
            active_tasks=active_tasks or [],
            risks=risks,
            uncertainties=uncertainties,
        )

        self._history.append(situation)
        logger.info("Synthesized situation v%d (%s)", self._current_version, summary)
        return situation

    def get_latest_situation(self) -> Optional[Situation]:
        return self._history[-1] if self._history else None
