"""Tamper-evident structured audit trail with SHA-256 hash chaining for Swarm Reasoning Engine (Task 64)."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any

from app.swarm.safety import scrub_swarm_secrets

logger = logging.getLogger(__name__)


class AuditRecord(dict):
    """Structured audit trail record with property access."""

    @property
    def record_hash(self) -> str:
        return self.get("record_hash") or self.get("hash") or self.get("entry_hash", "")

    @property
    def previous_hash(self) -> str:
        return self.get("previous_hash", "")

    @property
    def sequence_number(self) -> int:
        return self.get("sequence_number", 0)

    def __getattr__(self, name: str) -> Any:
        if name in self:
            return self[name]
        raise AttributeError(f"'AuditRecord' object has no attribute '{name}'")


class SwarmAuditor:
    """Manages an immutable, append-only, tamper-evident audit trail with SHA-256 hash chaining."""

    def __init__(self) -> None:
        self._audit_log: list[AuditRecord] = []
        self._last_hash: str = "0" * 64

    def record_event(
        self,
        event_type: str,
        actor: str,
        details: dict[str, Any] | None = None,
        session_id: str | None = None,
        agent_id: str | None = None,
        task_id: str | None = None,
    ) -> AuditRecord:
        """Record an audit event with SHA-256 hash chaining."""
        timestamp = datetime.now(timezone.utc).isoformat()
        sanitized_details = self._sanitize_dict(details or {})

        sequence_num = len(self._audit_log) + 1
        entry_data = {
            "sequence_number": sequence_num,
            "event_type": event_type,
            "actor": actor,
            "session_id": session_id,
            "agent_id": agent_id,
            "task_id": task_id,
            "timestamp": timestamp,
            "details": sanitized_details,
            "previous_hash": self._last_hash,
        }

        canonical_str = json.dumps(entry_data, sort_keys=True, default=str)
        current_hash = hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()

        entry = AuditRecord(
            {
                **entry_data,
                "hash": current_hash,
                "entry_hash": current_hash,
                "record_hash": current_hash,
            }
        )

        self._last_hash = current_hash
        self._audit_log.append(entry)
        logger.info(
            "SWARM_AUDIT_LOG: seq=%d event=%s actor=%s hash=%s",
            sequence_num,
            event_type,
            actor,
            current_hash,
        )
        return entry

    def record_action(
        self,
        action: str,
        session_id: str | None = None,
        data: dict[str, Any] | None = None,
        actor: str = "swarm_engine",
        **kwargs: Any,
    ) -> AuditRecord:
        """Convenience method for recording a swarm action with audit chaining."""
        return self.record_event(
            event_type=action,
            actor=actor,
            details=data,
            session_id=session_id,
            **kwargs,
        )

    def verify_integrity(self) -> bool:
        """Verify the cryptographic hash chain of the entire audit log."""
        expected_prev_hash = "0" * 64

        for entry in self._audit_log:
            entry_copy = {k: v for k, v in entry.items() if k not in ("hash", "entry_hash", "record_hash")}

            if entry_copy["previous_hash"] != expected_prev_hash:
                logger.error(
                    "AUDIT_CHAIN_BROKEN at seq=%d: previous_hash mismatch",
                    entry.get("sequence_number", -1),
                )
                return False

            canonical_str = json.dumps(entry_copy, sort_keys=True, default=str)
            computed_hash = hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()

            if computed_hash != entry["hash"]:
                logger.error(
                    "AUDIT_HASH_MISMATCH at seq=%d: recorded=%s computed=%s",
                    entry.get("sequence_number", -1),
                    entry["hash"],
                    computed_hash,
                )
                return False

            expected_prev_hash = entry["hash"]

        return True

    def verify_trail_integrity(self) -> bool:
        """Alias for verify_integrity."""
        return self.verify_integrity()

    def get_events(
        self,
        session_id: str | None = None,
        agent_id: str | None = None,
        task_id: str | None = None,
        limit: int = 100,
    ) -> list[AuditRecord]:
        """Retrieve audit log entries filtered by session, agent, or task."""
        results = self._audit_log
        if session_id:
            results = [e for e in results if e.get("session_id") == session_id]
        if agent_id:
            results = [e for e in results if e.get("agent_id") == agent_id]
        if task_id:
            results = [e for e in results if e.get("task_id") == task_id]
        return results[-limit:]

    def get_audit_trail(
        self,
        session_id: str | None = None,
        agent_id: str | None = None,
        task_id: str | None = None,
        limit: int = 100,
    ) -> list[AuditRecord]:
        """Alias for get_events."""
        return self.get_events(session_id=session_id, agent_id=agent_id, task_id=task_id, limit=limit)

    def _sanitize_dict(self, data: dict[str, Any]) -> dict[str, Any]:
        """Scrub secrets from audit details."""
        sanitized = {}
        for k, v in data.items():
            if isinstance(v, str):
                sanitized[k] = scrub_swarm_secrets(v)
            elif isinstance(v, dict):
                sanitized[k] = self._sanitize_dict(v)
            elif isinstance(v, list):
                sanitized[k] = [
                    self._sanitize_dict(x)
                    if isinstance(x, dict)
                    else (scrub_swarm_secrets(x) if isinstance(x, str) else x)
                    for x in v
                ]
            else:
                sanitized[k] = v
        return sanitized


swarm_auditor = SwarmAuditor()
