"""Cryptographic SHA-256 append-only hash-chained audit logger for Mission Engine (Task 66)."""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger("kairo.missions.audit")


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class MissionAuditRecord(BaseModel):
    """Cryptographically chained record of a mission lifecycle or governance event."""

    model_config = ConfigDict(extra="ignore")

    record_id: str = Field(default_factory=lambda: f"msnaud_{uuid.uuid4().hex[:12]}")
    mission_id: str
    event_type: (
        str  # GOAL_CREATED, STATE_TRANSITION, REPLAN_TRIGGERED, BLOCKER_DETECTED, HUMAN_OVERRIDE, VERIFIED
    )
    actor: str = "system"
    authority: str = "EXECUTE_LOW_RISK"
    details: dict[str, Any] = Field(default_factory=dict)
    previous_hash: str
    record_hash: str = ""
    timestamp: datetime = Field(default_factory=_now_utc)

    def calculate_hash(self) -> str:
        """Compute SHA-256 over record contents and previous link."""
        payload = {
            "record_id": self.record_id,
            "mission_id": self.mission_id,
            "event_type": self.event_type,
            "actor": self.actor,
            "authority": self.authority,
            "details": self.details,
            "previous_hash": self.previous_hash,
            "timestamp": self.timestamp.isoformat(),
        }
        serialized = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


class MissionAuditor:
    """Manages an unbroken SHA-256 hash-chained audit log for mission governance."""

    _GENESIS_HASH = "0" * 64

    def __init__(self) -> None:
        self._chain: list[MissionAuditRecord] = []

    def record_event(
        self,
        mission_id: str,
        event_type: str,
        details: dict[str, Any] | None = None,
        actor: str = "system",
        authority: str = "EXECUTE_LOW_RISK",
    ) -> MissionAuditRecord:
        """Append an event to the hash-chain."""
        prev_hash = self._chain[-1].record_hash if self._chain else self._GENESIS_HASH
        record = MissionAuditRecord(
            mission_id=mission_id,
            event_type=event_type,
            actor=actor,
            authority=authority,
            details=details or {},
            previous_hash=prev_hash,
        )
        record.record_hash = record.calculate_hash()
        self._chain.append(record)
        logger.debug(
            "MISSION_AUDIT_LOGGED: id=%s event=%s hash=%s",
            record.record_id,
            event_type,
            record.record_hash[:12],
        )
        return record

    def verify_integrity(self) -> bool:
        """Validate that all records match their hashes and link unbroken to genesis."""
        if not self._chain:
            return True

        expected_prev = self._GENESIS_HASH
        for idx, rec in enumerate(self._chain):
            if rec.previous_hash != expected_prev:
                logger.error(
                    "AUDIT_CHAIN_BROKEN: record %s at index %d has previous_hash %s != expected %s",
                    rec.record_id,
                    idx,
                    rec.previous_hash,
                    expected_prev,
                )
                return False

            recalculated = rec.calculate_hash()
            if recalculated != rec.record_hash:
                logger.error(
                    "AUDIT_HASH_TAMPERED: record %s at index %d has hash %s != recalculated %s",
                    rec.record_id,
                    idx,
                    rec.record_hash,
                    recalculated,
                )
                return False

            expected_prev = rec.record_hash

        return True

    def get_trail(self, mission_id: str | None = None) -> list[MissionAuditRecord]:
        """Return full audit log or filtered by mission_id."""
        if mission_id:
            return [r for r in self._chain if r.mission_id == mission_id]
        return list(self._chain)
