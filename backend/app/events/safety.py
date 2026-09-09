"""
Event payload safety, trace sanitization, and privileged event authorization guards.
"""

from __future__ import annotations

import re
from typing import Any
from app.evaluation.safety import KNOWN_SYNTHETIC_SECRETS, SECRET_PATTERNS
from app.events.schemas import Event, EventSource


# Privileged events that must NEVER be emitted by untrusted sources or LLM outputs (Section 78 & 79)
PRIVILEGED_EVENT_TYPES = {
    "security.allowed",
    "security.override",
    "approval.granted",
    "device.authorized",
    "device.revoked",
    "permission.elevated",
}

# Trusted sources permitted to emit privileged security events
TRUSTED_SECURITY_SOURCES = {
    EventSource.SECURITY,
    EventSource.APPROVAL,
    EventSource.SYSTEM,
    "security",
    "approval",
    "system",
    "security_center",
    "approval_manager",
}


class EventSecurityGuard:
    """Safeguards the Event Bus against secret leakage, event forgery, and prompt injection."""

    @classmethod
    def sanitize_payload(cls, data: Any) -> Any:
        """Recursively redact secrets and sensitive credentials from event payloads."""
        if isinstance(data, dict):
            clean = {}
            for k, v in data.items():
                k_lower = str(k).lower()
                if any(s in k_lower for s in ("password", "secret", "token", "api_key", "private_key", "authorization")):
                    clean[k] = "[REDACTED]"
                else:
                    clean[k] = cls.sanitize_payload(v)
            return clean
        elif isinstance(data, list):
            return [cls.sanitize_payload(item) for item in data]
        elif isinstance(data, str):
            sanitized = data
            for secret in KNOWN_SYNTHETIC_SECRETS:
                sanitized = sanitized.replace(secret, "[REDACTED_SECRET]")
            for pattern in SECRET_PATTERNS:
                sanitized = pattern.sub(r"\1: [REDACTED]", sanitized)
            return sanitized
        return data

    @classmethod
    def sanitize_event(cls, event: Event) -> Event:
        """Return a copy of the event with sanitized payload and metadata."""
        clean_payload = cls.sanitize_payload(event.payload or {})
        clean_meta = (
            cls.sanitize_payload(event.metadata)
            if isinstance(event.metadata, dict)
            else {}
        )
        event_dict = event.model_dump()
        event_dict["payload"] = clean_payload
        event_dict["metadata"] = clean_meta
        return Event.model_validate(event_dict)

    @classmethod
    def validate_publication_authority(
        cls,
        event_or_type: Any,
        source: Any = None,
    ) -> None:
        """Verify that untrusted sources cannot forge privileged security events (Section 78)."""
        if isinstance(event_or_type, Event):
            event_type = event_or_type.event_type
            source_raw = event_or_type.source
        else:
            event_type = str(event_or_type)
            source_raw = source

        if event_type in PRIVILEGED_EVENT_TYPES:
            source_val = (
                source_raw.value
                if isinstance(source_raw, EventSource)
                else str(source_raw)
            )
            trusted_vals = {
                s.value if isinstance(s, EventSource) else str(s)
                for s in TRUSTED_SECURITY_SOURCES
            }
            if source_val not in trusted_vals:
                raise PermissionError(
                    f"Event forgery rejected: Untrusted source '{source_val}' attempted to publish privileged event '{event_type}'."
                )
