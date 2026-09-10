"""Tamper-evident structured audit trail for Incident Response Engine (Task 61)."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any

from app.incident_response.safety import scrub_incident_secrets

logger = logging.getLogger(__name__)


class IncidentAuditor:
    """Manages an immutable, append-only, tamper-evident audit trail with SHA-256 hash chaining."""

    def __init__(self) -> None:
        self._audit_log: list[dict[str, Any]] = []
        self._last_hash: str = "0" * 64

    def record_event(
        self,
        event_type: str,
        actor: str,
        details: dict[str, Any] | None = None,
        incident_id: str | None = None,
    ) -> dict[str, Any]:
        """Record an audit event with SHA-256 hash chaining."""
        timestamp = datetime.now(timezone.utc).isoformat()
        sanitized_details = self._sanitize_dict(details or {})

        sequence_num = len(self._audit_log) + 1
        entry_data = {
            "sequence_number": sequence_num,
            "event_type": event_type,
            "actor": actor,
            "incident_id": incident_id,
            "timestamp": timestamp,
            "details": sanitized_details,
            "previous_hash": self._last_hash,
        }

        canonical_str = json.dumps(entry_data, sort_keys=True, default=str)
        current_hash = hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()

        entry = {
            **entry_data,
            "hash": current_hash,
            "entry_hash": current_hash,
        }

        self._last_hash = current_hash
        self._audit_log.append(entry)
        logger.info(
            "INCIDENT_AUDIT: %s by %s on %s [hash=%s]", event_type, actor, incident_id, current_hash[:8]
        )
        return entry

    def verify_integrity(self) -> bool:
        """Verify cryptographic hash chaining across all audit entries."""
        expected_prev = "0" * 64
        for entry in self._audit_log:
            if entry["previous_hash"] != expected_prev:
                return False
            payload = {
                "sequence_number": entry.get("sequence_number", 0),
                "event_type": entry["event_type"],
                "actor": entry["actor"],
                "incident_id": entry["incident_id"],
                "timestamp": entry["timestamp"],
                "details": entry["details"],
                "previous_hash": entry["previous_hash"],
            }
            computed_hash = hashlib.sha256(
                json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
            ).hexdigest()
            if computed_hash != entry["hash"]:
                return False
            expected_prev = entry["hash"]
        return True

    verify_chain = verify_integrity

    def get_events(
        self,
        incident_id: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Retrieve audit log entries, optionally filtered by incident_id."""
        if incident_id:
            filtered = [e for e in self._audit_log if e.get("incident_id") == incident_id]
            return filtered[-limit:]
        return self._audit_log[-limit:]

    def _sanitize_dict(self, d: dict[str, Any]) -> dict[str, Any]:
        """Scrub secret credentials from dictionary values."""
        clean: dict[str, Any] = {}
        for k, v in d.items():
            if isinstance(v, str):
                clean[k] = scrub_incident_secrets(v)
            elif isinstance(v, dict):
                clean[k] = self._sanitize_dict(v)
            elif isinstance(v, list):
                clean[k] = [
                    self._sanitize_dict(i)
                    if isinstance(i, dict)
                    else (scrub_incident_secrets(i) if isinstance(i, str) else i)
                    for i in v
                ]
            else:
                clean[k] = v
        return clean


incident_auditor = IncidentAuditor()
