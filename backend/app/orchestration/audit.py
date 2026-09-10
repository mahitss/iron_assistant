"""Tamper-evident structured audit trail for Kairo Orchestration Engine (Task 59)."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any

from app.orchestration.safety import scrub_orchestration_secrets

logger = logging.getLogger(__name__)


class OrchestrationAuditor:
    """Manages an immutable, append-only, tamper-evident audit trail for orchestration actions."""

    def __init__(self) -> None:
        self._audit_log: list[dict[str, Any]] = []
        self._last_hash: str = "0" * 64

    def record_event(
        self,
        event_type: str,
        actor: str,
        details: dict[str, Any],
        orchestration_id: str | None = None,
        task_id: str | None = None,
    ) -> dict[str, Any]:
        """Record an orchestration event with SHA-256 hash chaining."""
        timestamp = datetime.now(timezone.utc).isoformat()

        # Ensure sensitive details are scrubbed
        sanitized_details = self._sanitize_dict(details)

        entry_data = {
            "event_type": event_type,
            "actor": actor,
            "orchestration_id": orchestration_id,
            "task_id": task_id,
            "timestamp": timestamp,
            "details": sanitized_details,
            "previous_hash": self._last_hash,
        }

        canonical_str = json.dumps(entry_data, sort_keys=True, default=str)
        current_hash = hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()

        entry = {
            **entry_data,
            "hash": current_hash,
        }

        self._last_hash = current_hash
        self._audit_log.append(entry)
        logger.info("ORCHESTRATION_AUDIT: %s by %s [hash=%s]", event_type, actor, current_hash[:8])
        return entry

    def verify_integrity(self) -> bool:
        """Verify the cryptographic integrity of the audit chain."""
        expected_prev = "0" * 64
        for entry in self._audit_log:
            if entry["previous_hash"] != expected_prev:
                return False
            payload = {
                "event_type": entry["event_type"],
                "actor": entry["actor"],
                "orchestration_id": entry["orchestration_id"],
                "task_id": entry["task_id"],
                "timestamp": entry["timestamp"],
                "details": entry["details"],
                "previous_hash": entry["previous_hash"],
            }
            computed_hash = hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()
            if computed_hash != entry["hash"]:
                return False
            expected_prev = entry["hash"]
        return True

    def get_events(
        self,
        orchestration_id: str | None = None,
        event_type: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Retrieve recent audit events matching optional filters."""
        results = self._audit_log
        if orchestration_id:
            results = [e for e in results if e["orchestration_id"] == orchestration_id]
        if event_type:
            results = [e for e in results if e["event_type"] == event_type]
        return results[-limit:]

    def _sanitize_dict(self, d: dict[str, Any]) -> dict[str, Any]:
        sanitized = {}
        for k, v in d.items():
            if isinstance(v, str):
                sanitized[k] = scrub_orchestration_secrets(v)
            elif isinstance(v, dict):
                sanitized[k] = self._sanitize_dict(v)
            elif isinstance(v, list):
                sanitized[k] = [
                    self._sanitize_dict(item) if isinstance(item, dict)
                    else (scrub_orchestration_secrets(item) if isinstance(item, str) else item)
                    for item in v
                ]
            else:
                sanitized[k] = v
        return sanitized


orchestration_auditor = OrchestrationAuditor()
