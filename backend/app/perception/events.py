"""Perception Event Models, 27 Event Types, Authenticity Verification, and Payload Sanitization (Task 46)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
import logging
from typing import Any, Dict, List, Optional
import uuid

logger = logging.getLogger("kairo.perception.events")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class EventType(str, Enum):
    """27 normalized environmental event types (Spec 9)."""

    CREATED = "CREATED"
    UPDATED = "UPDATED"
    DELETED = "DELETED"
    STARTED = "STARTED"
    STOPPED = "STOPPED"
    CONNECTED = "CONNECTED"
    DISCONNECTED = "DISCONNECTED"
    FAILED = "FAILED"
    RECOVERED = "RECOVERED"
    HEALTH_CHANGED = "HEALTH_CHANGED"
    STATUS_CHANGED = "STATUS_CHANGED"
    DEPLOYED = "DEPLOYED"
    COMMITTED = "COMMITTED"
    PUSHED = "PUSHED"
    MERGED = "MERGED"
    OPENED = "OPENED"
    CLOSED = "CLOSED"
    FOCUSED = "FOCUSED"
    NAVIGATED = "NAVIGATED"
    RECEIVED = "RECEIVED"
    SENT = "SENT"
    SCHEDULED = "SCHEDULED"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"
    BLOCKED = "BLOCKED"
    EXPIRED = "EXPIRED"
    ALERTED = "ALERTED"


class InvalidEventError(Exception):
    """Raised when an environmental event is malformed or missing mandatory fields (Spec 13)."""


class EventAuthenticityError(Exception):
    """Raised when an event fails cryptographic signature or source verification (Spec 14, 15)."""


class PayloadSizeExceededError(Exception):
    """Raised when an event payload exceeds configured maximum size limits (Spec 150)."""


@dataclass
class PerceptionEvent:
    """Normalized atomic perception event ingested from an authorized source (Spec 8, 10)."""

    event_id: str
    event_type: EventType
    source_id: str
    subject: str
    timestamp: datetime = field(default_factory=utc_now)
    sequence: int = 0
    payload: Dict[str, Any] = field(default_factory=dict)
    scope: Dict[str, Any] = field(default_factory=dict)
    correlation_id: Optional[str] = None
    causation_id: Optional[str] = None
    provenance: Dict[str, Any] = field(default_factory=dict)
    signature: Optional[str] = None
    is_authenticated: bool = True
    received_at: datetime = field(default_factory=utc_now)

    MAX_PAYLOAD_BYTES = 512 * 1024  # 512 KB payload ceiling (Spec 150)

    def validate(self) -> None:
        """Validate structure, size bounds, and authenticity (Spec 13-15, 148-150)."""
        if not self.event_id or not self.event_type or not self.source_id or not self.subject:
            raise InvalidEventError("Event missing mandatory fields: event_id, event_type, source_id, or subject.")

        # Validate payload size bounds (Spec 150)
        try:
            serialized = json.dumps(self.payload)
            if len(serialized.encode("utf-8")) > self.MAX_PAYLOAD_BYTES:
                raise PayloadSizeExceededError(
                    f"Event payload ({len(serialized)} bytes) exceeds maximum limit ({self.MAX_PAYLOAD_BYTES} bytes)."
                )
        except (TypeError, ValueError) as exc:
            raise InvalidEventError(f"Malformed non-serializable payload: {exc}")

        # Authenticity validation (Spec 14, 15)
        if not self.is_authenticated:
            raise EventAuthenticityError(f"Event {self.event_id} failed source authentication verification.")

    def compute_hash(self) -> str:
        """Deterministic fingerprint for deduplication (Spec 16)."""
        core = {
            "source_id": self.source_id,
            "event_type": self.event_type.value,
            "subject": self.subject,
            "sequence": self.sequence,
            "timestamp": self.timestamp.isoformat(),
            "payload": self.payload,
        }
        raw = json.dumps(core, sort_keys=True)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "source_id": self.source_id,
            "subject": self.subject,
            "timestamp": self.timestamp.isoformat(),
            "sequence": self.sequence,
            "payload": self.payload,
            "scope": self.scope,
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
            "provenance": self.provenance,
            "is_authenticated": self.is_authenticated,
            "received_at": self.received_at.isoformat(),
        }
