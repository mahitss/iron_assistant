"""Periodic executive state snapshots and staleness invalidation (INVARIANTS 14-18)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
import uuid

from app.executive_memory.schemas import ExecutiveStateSchema


class SnapshotItem:
    def __init__(self, snapshot_id: str, project_id: str, state: dict[str, Any], source_refs: list[str] | None = None):
        self.snapshot_id = snapshot_id
        self.project_id = project_id
        self.state = state
        self.source_refs = source_refs or []
        self.is_stale = False
        self.is_valid = True
        self.invalidation_reason: str | None = None
        self.created_at = datetime.now(UTC)


class SnapshotManager:
    """Creates periodic snapshots for fast reconstruction and invalidates on material changes."""

    def __init__(self) -> None:
        # snapshot_id -> snapshot dict
        self._snapshots: dict[str, dict[str, Any]] = {}
        # project_id -> list of snapshot_ids
        self._project_snapshots: dict[str, list[str]] = {}
        # project_id -> latest SnapshotItem
        self._snapshot_items: dict[str, SnapshotItem] = {}

    def create_snapshot(
        self,
        project_id: str,
        state: dict[str, Any],
        source_refs: list[str] | None = None,
    ) -> SnapshotItem:
        """INVARIANT 14 & 16: Captures snapshot item referencing underlying state sources."""
        sid = f"snp_{uuid.uuid4().hex[:12]}"
        item = SnapshotItem(
            snapshot_id=sid,
            project_id=project_id,
            state=state,
            source_refs=source_refs,
        )
        self._snapshot_items[project_id] = item
        return item

    def invalidate_snapshot(self, project_id: str, reason: str = "Material state change") -> SnapshotItem | None:
        """INVARIANT 18: Invalidate existing snapshot for project upon material state changes."""
        item = self._snapshot_items.get(project_id)
        if item:
            item.is_stale = True
            item.is_valid = False
            item.invalidation_reason = reason
        self.invalidate_snapshots(project_id, reason=reason)
        return item

    def capture_snapshot(
        self,
        executive_state: ExecutiveStateSchema,
        source_version_hash: str = "",
    ) -> dict[str, Any]:
        """INVARIANT 14 & 16: Captures snapshot referencing underlying state sources."""
        sid = f"snp_{uuid.uuid4().hex[:12]}"
        now = datetime.now(UTC)
        record = {
            "snapshot_id": sid,
            "state_id": executive_state.state_id,
            "scope": executive_state.scope,
            "scope_id": executive_state.scope_id,
            "payload": executive_state.model_dump(),
            "source_version_hash": source_version_hash,
            "is_valid": True,
            "captured_at": now.isoformat(),
        }
        self._snapshots[sid] = record
        if executive_state.scope_id:
            self._project_snapshots.setdefault(executive_state.scope_id, []).append(sid)
        return record

    def invalidate_snapshots(self, scope_id: str, reason: str = "Material state change") -> int:
        """INVARIANT 18: Invalidate existing snapshots upon material state changes."""
        sids = self._project_snapshots.get(scope_id, [])
        count = 0
        for sid in sids:
            if sid in self._snapshots and self._snapshots[sid]["is_valid"]:
                self._snapshots[sid]["is_valid"] = False
                self._snapshots[sid]["invalidation_reason"] = reason
                count += 1
        return count

    def get_latest_valid_snapshot(self, scope_id: str) -> dict[str, Any] | None:
        sids = self._project_snapshots.get(scope_id, [])
        for sid in reversed(sids):
            snap = self._snapshots.get(sid)
            if snap and snap.get("is_valid"):
                return snap
        return None
