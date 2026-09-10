"""Snapshot management, baseline hashing, immutability, and freshness tracking for Simulation."""

from __future__ import annotations

import copy
import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from app.simulation.safety import scrub_secrets
from app.simulation.schemas import SimulationSnapshot


def compute_state_hash(state: dict[str, Any]) -> str:
    """Computes a deterministic canonical SHA-256 hash of a dictionary state."""
    canonical_json = json.dumps(state, sort_keys=True, default=str)
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


class SnapshotManager:
    """Manages immutable simulation baseline snapshots with cryptographic hashing and freshness checks."""

    def __init__(self, max_freshness_seconds: int = 300) -> None:
        self.max_freshness_seconds = max_freshness_seconds
        self._snapshots: dict[str, SimulationSnapshot] = {}

    def capture_snapshot(
        self,
        source_entity: str = "digital_twin",
        world_state: dict[str, Any] | None = None,
        digital_twin_state: dict[str, Any] | None = None,
        telemetry_state: dict[str, Any] | None = None,
        provenance: dict[str, Any] | None = None,
    ) -> SimulationSnapshot:
        """Captures a new immutable snapshot from provided or observed environment states."""
        clean_world = scrub_secrets(copy.deepcopy(world_state or {}))
        clean_twin = scrub_secrets(copy.deepcopy(digital_twin_state or {}))
        clean_telemetry = scrub_secrets(copy.deepcopy(telemetry_state or {}))

        composite_state = {
            "world": clean_world,
            "digital_twin": clean_twin,
            "telemetry": clean_telemetry,
        }
        baseline_hash = compute_state_hash(composite_state)
        snapshot_id = f"snap_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)

        snapshot = SimulationSnapshot(
            snapshot_id=snapshot_id,
            source_entity=source_entity,
            world_state=clean_world,
            digital_twin_state=clean_twin,
            telemetry_state=clean_telemetry,
            captured_at=now,
            baseline_hash=baseline_hash,
            is_stale=False,
            staleness_reason=None,
            provenance=provenance or {"captured_by": "SimulationSnapshotManager", "version": "1.0"},
        )

        # Store immutable clone
        self._snapshots[snapshot_id] = snapshot.model_copy(deep=True)
        return snapshot.model_copy(deep=True)

    def get_snapshot(self, snapshot_id: str) -> SimulationSnapshot | None:
        """Retrieves a deep clone of a snapshot, ensuring caller cannot mutate the stored record."""
        snap = self._snapshots.get(snapshot_id)
        if snap is None:
            return None
        return snap.model_copy(deep=True)

    def verify_freshness(
        self,
        snapshot_id: str,
        current_state: dict[str, Any] | None = None,
    ) -> tuple[bool, str | None]:
        """Checks if a snapshot is still fresh based on time and optional current real-state hash comparison.

        Returns (is_fresh, reason_if_stale).
        """
        snap = self.get_snapshot(snapshot_id)
        if snap is None:
            return False, f"Snapshot '{snapshot_id}' does not exist."

        now = datetime.now(timezone.utc)
        age_seconds = (now - snap.captured_at).total_seconds()

        if age_seconds > self.max_freshness_seconds:
            reason = f"Snapshot age ({age_seconds:.1f}s) exceeds max threshold ({self.max_freshness_seconds}s)."
            self._mark_stale(snapshot_id, reason)
            return False, reason

        if current_state is not None:
            current_clean = scrub_secrets(copy.deepcopy(current_state))
            current_hash = compute_state_hash(current_clean)
            if current_hash != snap.baseline_hash:
                reason = "Current real-world state diverged from snapshot baseline hash."
                self._mark_stale(snapshot_id, reason)
                return False, reason

        return True, None

    def _mark_stale(self, snapshot_id: str, reason: str) -> None:
        if snapshot_id in self._snapshots:
            stored = self._snapshots[snapshot_id]
            self._snapshots[snapshot_id] = stored.model_copy(
                update={"is_stale": True, "staleness_reason": reason}
            )

    def list_snapshots(self) -> list[SimulationSnapshot]:
        """Returns deep copies of all tracked snapshots."""
        return [s.model_copy(deep=True) for s in self._snapshots.values()]


# Global default manager instance
snapshot_manager = SnapshotManager()
