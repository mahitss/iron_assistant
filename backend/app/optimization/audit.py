"""Tamper-evident structured audit trail for Continuous Self-Optimization & Adaptive Control Engine (Task 62)."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any

from app.optimization.safety import scrub_optimization_secrets

logger = logging.getLogger(__name__)


class OptimizationAuditor:
    """Manages an immutable, append-only, tamper-evident audit trail with SHA-256 hash chaining."""

    def __init__(self) -> None:
        self._audit_log: list[dict[str, Any]] = []
        self._last_hash: str = "0" * 64

    def record_event(
        self,
        event_type: str,
        actor: str,
        details: dict[str, Any] | None = None,
        recommendation_id: str | None = None,
        change_set_id: str | None = None,
        experiment_id: str | None = None,
    ) -> dict[str, Any]:
        """Record an audit event with SHA-256 hash chaining."""
        timestamp = datetime.now(timezone.utc).isoformat()
        sanitized_details = self._sanitize_dict(details or {})

        sequence_num = len(self._audit_log) + 1
        entry_data = {
            "sequence_number": sequence_num,
            "event_type": event_type,
            "actor": actor,
            "recommendation_id": recommendation_id,
            "change_set_id": change_set_id,
            "experiment_id": experiment_id,
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
            "OPTIMIZATION_AUDIT: %s by %s [change_set=%s, hash=%s]",
            event_type,
            actor,
            change_set_id,
            current_hash[:8],
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
                "recommendation_id": entry.get("recommendation_id"),
                "change_set_id": entry.get("change_set_id"),
                "experiment_id": entry.get("experiment_id"),
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
        change_set_id: str | None = None,
        experiment_id: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Retrieve audit log entries, optionally filtered."""
        filtered = self._audit_log
        if change_set_id:
            filtered = [e for e in filtered if e.get("change_set_id") == change_set_id]
        if experiment_id:
            filtered = [e for e in filtered if e.get("experiment_id") == experiment_id]
        return filtered[-limit:]

    def _sanitize_dict(self, d: dict[str, Any]) -> dict[str, Any]:
        """Scrub secret credentials from dictionary values."""
        clean: dict[str, Any] = {}
        for k, v in d.items():
            if isinstance(v, str):
                clean[k] = scrub_optimization_secrets(v)
            elif isinstance(v, dict):
                clean[k] = self._sanitize_dict(v)
            elif isinstance(v, list):
                clean[k] = [
                    self._sanitize_dict(item)
                    if isinstance(item, dict)
                    else (scrub_optimization_secrets(item) if isinstance(item, str) else item)
                    for item in v
                ]
            else:
                clean[k] = v
        return clean


optimization_auditor = OptimizationAuditor()
