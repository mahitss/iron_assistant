"""Snapshot manager with cryptographic checksum verification and corruption isolation (Task 39, Spec 29-35)."""

import hashlib
import json
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from app.state.schemas import StateSnapshot

logger = logging.getLogger("kairo.state.snapshots")


class SnapshotIntegrityError(Exception):
    """Raised when snapshot checksum or schema validation fails."""


class SnapshotManager:
    """Manages projection snapshots, deterministic integrity checksums, and corruption defense."""

    def __init__(self) -> None:
        self._snapshots: dict[str, list[StateSnapshot]] = {}

    @classmethod
    def compute_checksum(cls, payload: dict[str, Any]) -> str:
        """Computes deterministic SHA-256 checksum of canonical JSON payload."""
        canonical_bytes = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
        return hashlib.sha256(canonical_bytes).hexdigest()

    def create_snapshot(
        self,
        projection_identifier: str,
        state_version: int,
        payload: dict[str, Any],
        schema_version: int = 1,
    ) -> StateSnapshot:
        """Creates and stores a validated snapshot of a projection."""
        checksum = self.compute_checksum(payload)
        snapshot = StateSnapshot(
            id=f"snp_{uuid.uuid4().hex[:16]}",
            projection_identifier=projection_identifier,
            state_version=state_version,
            schema_version=schema_version,
            checksum=checksum,
            payload=payload,
            created_at=datetime.now(UTC),
        )

        if projection_identifier not in self._snapshots:
            self._snapshots[projection_identifier] = []
        self._snapshots[projection_identifier].append(snapshot)

        logger.info(
            "Created snapshot %s for '%s' (v%d, checksum=%s)",
            snapshot.id,
            projection_identifier,
            state_version,
            checksum[:8],
        )
        return snapshot

    def load_latest_valid_snapshot(
        self,
        projection_identifier: str,
        required_schema_version: int = 1,
    ) -> StateSnapshot | None:
        """Loads latest valid snapshot, verifying checksum integrity and schema version.
        
        If the latest snapshot is corrupted, falls back to the previous valid snapshot.
        """
        snapshots = self._snapshots.get(projection_identifier, [])
        if not snapshots:
            return None

        # Iterate in reverse (latest first)
        for snapshot in reversed(snapshots):
            # 1. Verify schema version compatibility
            if snapshot.schema_version != required_schema_version:
                logger.warning(
                    "Snapshot %s schema version %d incompatible with required %d; skipping",
                    snapshot.id,
                    snapshot.schema_version,
                    required_schema_version,
                )
                continue

            # 2. Verify deterministic checksum integrity
            expected_checksum = self.compute_checksum(snapshot.payload)
            if snapshot.checksum != expected_checksum:
                logger.error(
                    "Snapshot %s corrupted! Checksum mismatch: expected %s, found %s",
                    snapshot.id,
                    expected_checksum,
                    snapshot.checksum,
                )
                continue  # Skip corrupt snapshot and fallback to previous

            # Valid snapshot found
            return snapshot

        return None

    def clear(self) -> None:
        """Clears in-memory snapshots (testing only)."""
        self._snapshots.clear()


# Global snapshot manager instance
snapshot_manager = SnapshotManager()
