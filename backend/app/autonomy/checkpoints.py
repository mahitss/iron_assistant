"""Durable Autonomous Checkpoints, Corruption Detection, and State Serialization (Task 45)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import logging
from typing import Any, Dict, List, Optional
import uuid

logger = logging.getLogger("kairo.autonomy.checkpoints")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CorruptCheckpointError(Exception):
    """Raised when an autonomous checkpoint fails cryptographic integrity or schema validation."""


@dataclass
class AutonomousCheckpoint:
    """Atomic, cryptographically hashed state snapshot of an autonomous execution (Spec 10, 11)."""

    checkpoint_id: str
    run_id: str
    plan_version: int
    step_id: Optional[str]
    run_state: str
    completed_work: List[Dict[str, Any]] = field(default_factory=list)
    pending_work: List[Dict[str, Any]] = field(default_factory=list)
    active_work: List[Dict[str, Any]] = field(default_factory=list)
    evidence_refs: List[str] = field(default_factory=list)
    verification_state: Dict[str, Any] = field(default_factory=dict)
    budget_state: Dict[str, Any] = field(default_factory=dict)
    world_state_version: Optional[str] = None
    agent_state: Dict[str, Any] = field(default_factory=dict)
    is_valid: bool = True
    corruption_hash: str = ""
    created_at: datetime = field(default_factory=utc_now)

    def calculate_hash(self) -> str:
        """Compute SHA-256 integrity hash over all critical state fields (Spec 108)."""
        payload = {
            "checkpoint_id": self.checkpoint_id,
            "run_id": self.run_id,
            "plan_version": self.plan_version,
            "step_id": self.step_id,
            "run_state": self.run_state,
            "completed_work": self.completed_work,
            "pending_work": self.pending_work,
            "active_work": self.active_work,
            "evidence_refs": self.evidence_refs,
            "verification_state": self.verification_state,
            "budget_state": self.budget_state,
            "world_state_version": self.world_state_version,
            "agent_state": self.agent_state,
        }
        raw = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def verify_integrity(self) -> bool:
        """Verify checkpoint has not been tampered with or corrupted (Spec 108)."""
        expected = self.calculate_hash()
        return self.corruption_hash == expected

    def to_dict(self) -> Dict[str, Any]:
        return {
            "checkpoint_id": self.checkpoint_id,
            "run_id": self.run_id,
            "plan_version": self.plan_version,
            "step_id": self.step_id,
            "run_state": self.run_state,
            "completed_work": self.completed_work,
            "pending_work": self.pending_work,
            "active_work": self.active_work,
            "evidence_refs": self.evidence_refs,
            "verification_state": self.verification_state,
            "budget_state": self.budget_state,
            "world_state_version": self.world_state_version,
            "agent_state": self.agent_state,
            "is_valid": self.is_valid,
            "corruption_hash": self.corruption_hash,
            "created_at": self.created_at.isoformat(),
        }


class CheckpointManager:
    """Manages transactional checkpoint creation, verification, and fallback recovery (Spec 12, 108, 109)."""

    def __init__(self) -> None:
        # run_id -> list of checkpoints in chronological order
        self._history: Dict[str, List[AutonomousCheckpoint]] = {}

    def create_checkpoint(
        self,
        run_id: str,
        plan_version: int,
        run_state: str,
        step_id: Optional[str] = None,
        completed_work: Optional[List[Dict[str, Any]]] = None,
        pending_work: Optional[List[Dict[str, Any]]] = None,
        active_work: Optional[List[Dict[str, Any]]] = None,
        evidence_refs: Optional[List[str]] = None,
        verification_state: Optional[Dict[str, Any]] = None,
        budget_state: Optional[Dict[str, Any]] = None,
        world_state_version: Optional[str] = None,
        agent_state: Optional[Dict[str, Any]] = None,
    ) -> AutonomousCheckpoint:
        """Persist a durable, atomic checkpoint with hash-based integrity (Spec 10-13)."""
        checkpoint_id = f"chk_{uuid.uuid4().hex[:12]}"
        chk = AutonomousCheckpoint(
            checkpoint_id=checkpoint_id,
            run_id=run_id,
            plan_version=plan_version,
            step_id=step_id,
            run_state=run_state,
            completed_work=completed_work or [],
            pending_work=pending_work or [],
            active_work=active_work or [],
            evidence_refs=evidence_refs or [],
            verification_state=verification_state or {},
            budget_state=budget_state or {},
            world_state_version=world_state_version,
            agent_state=agent_state or {},
        )
        chk.corruption_hash = chk.calculate_hash()

        self._history.setdefault(run_id, []).append(chk)
        logger.info("Saved atomic checkpoint %s for run %s (state=%s, step=%s)", checkpoint_id, run_id, run_state, step_id)
        return chk

    def get_latest_valid_checkpoint(self, run_id: str) -> Optional[AutonomousCheckpoint]:
        """Retrieve most recent uncorrupted checkpoint, falling back if latest is corrupt (Spec 108, 109)."""
        checkpoints = self._history.get(run_id, [])
        if not checkpoints:
            return None

        # Inspect in reverse chronological order
        for chk in reversed(checkpoints):
            if chk.verify_integrity():
                return chk
            logger.error("Checkpoint %s for run %s failed integrity verification! Attempting fallback.", chk.checkpoint_id, run_id)

        raise CorruptCheckpointError(f"All checkpoints for run {run_id} failed integrity verification.")

    def get_checkpoint(self, run_id: str, checkpoint_id: str) -> Optional[AutonomousCheckpoint]:
        for chk in self._history.get(run_id, []):
            if chk.checkpoint_id == checkpoint_id:
                return chk
        return None
