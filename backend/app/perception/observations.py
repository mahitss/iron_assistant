"""Observation Models, Freshness Scoring, and Confidence Principles (Task 46)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
from typing import Any, Dict, Optional
import uuid

from app.perception.events import EventType, PerceptionEvent
from app.perception.sources import PerceptionSource, SourceType

logger = logging.getLogger("kairo.perception.observations")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class Observation:
    """Structured perception observation representing an empirical fact observed from environment (Spec 6, 7)."""

    observation_id: str
    source_id: str
    source_type: SourceType
    subject: str
    event_type: EventType
    payload_reference: str  # Reference or digest, minimizing raw data persistence (Spec 172)
    observed_at: datetime
    received_at: datetime
    scope: Dict[str, Any] = field(default_factory=dict)
    provenance: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0  # Contextual confidence 0.0 to 1.0 (Spec 135)
    correlation_id: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)

    @property
    def latency_ms(self) -> float:
        """Measure ingestion delay between observed and received timestamp (Spec 23)."""
        diff = (self.received_at - self.observed_at).total_seconds()
        return max(0.0, diff * 1000.0)

    @property
    def age_seconds(self) -> float:
        """Measure real-time freshness of the observation (Spec 61, 118)."""
        return max(0.0, (utc_now() - self.observed_at).total_seconds())

    def is_fresh(self, ttl_seconds: float = 60.0) -> bool:
        """Check if observation freshness remains within SLA window."""
        return self.age_seconds <= ttl_seconds

    @classmethod
    def from_event(
        cls,
        event: PerceptionEvent,
        source: PerceptionSource,
        payload_ref: Optional[str] = None,
        override_confidence: Optional[float] = None,
    ) -> Observation:
        """Construct structured observation from validated perception event and source (Spec 6, 7).
        
        CRITICAL: Observation describes WHAT was observed, NOT why it happened! (Spec 7)
        Confidence reflects source reliability and validation, NOT absolute truth! (Spec 136)
        """
        conf = override_confidence if override_confidence is not None else source.reliability
        obs_id = f"obs_{uuid.uuid4().hex[:12]}"
        pref = payload_ref or f"payload://events/{event.event_id}"

        return cls(
            observation_id=obs_id,
            source_id=source.source_id,
            source_type=source.type,
            subject=event.subject,
            event_type=event.event_type,
            payload_reference=pref,
            observed_at=event.timestamp,
            received_at=event.received_at,
            scope=dict(event.scope),
            provenance={
                **event.provenance,
                "source_name": source.name,
                "source_reliability": source.reliability,
                "source_privacy": source.privacy_level.value,
            },
            confidence=max(0.0, min(1.0, conf)),
            correlation_id=event.correlation_id,
            data=event.payload,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "observation_id": self.observation_id,
            "source_id": self.source_id,
            "source_type": self.source_type.value,
            "subject": self.subject,
            "event_type": self.event_type.value,
            "payload_reference": self.payload_reference,
            "observed_at": self.observed_at.isoformat(),
            "received_at": self.received_at.isoformat(),
            "age_seconds": round(self.age_seconds, 2),
            "latency_ms": round(self.latency_ms, 2),
            "confidence": round(self.confidence, 3),
            "correlation_id": self.correlation_id,
            "scope": self.scope,
            "provenance": self.provenance,
            "data": self.data,
        }
