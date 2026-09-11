"""ContextSnapshotManager: Immutable snapshot persistence, audit, and replay (Task 69)."""

import logging
from datetime import UTC, datetime
from typing import Any

from app.context.universal_schemas import ContextPackage, ContextSnapshot

logger = logging.getLogger("kairo.context.snapshots")


class ContextSnapshotManager:
    """Manages immutable snapshots of assembled context for auditing, debugging, and deterministic replay."""

    def __init__(self) -> None:
        self._snapshots: dict[str, ContextSnapshot] = {}

    def create_snapshot(
        self,
        package: ContextPackage,
        metadata: dict[str, Any] | None = None,
    ) -> ContextSnapshot:
        """Create and store an immutable snapshot of an assembled context package."""
        now = datetime.now(UTC)
        snapshot_id = f"snap_{int(now.timestamp() * 1000)}_{package.context_id[:8]}"

        selected_dicts = [
            {
                "item_id": it.item_id,
                "context_type": it.context_type.value,
                "title": it.title,
                "content": it.content,
                "hierarchy_level": it.hierarchy_level.value,
                "priority_tier": it.priority_tier.value,
                "relevance_score": it.relevance_score,
                "source_id": it.source_id,
                "source_type": it.source_type,
                "environment": it.environment,
                "reason": it.reason,
            }
            for it in package.items
        ]

        conflicts_dicts = [c.model_dump() for c in package.conflicts]
        missing_dicts = [m.model_dump() for m in package.missing_context]

        snap = ContextSnapshot(
            snapshot_id=snapshot_id,
            request_id=package.request_id,
            tenant_id=package.tenant_id,
            user_id=package.user_id,
            environment=package.environment,
            token_estimate=package.token_estimate,
            quality_score=package.quality_score.overall_score,
            selected_items=selected_dicts,
            retrieval_reasons=package.retrieval_reasons,
            missing_context=missing_dicts,
            conflicts=conflicts_dicts,
            metadata=metadata or {},
            created_at=now,
        )

        self._snapshots[snapshot_id] = snap
        return snap

    def get_snapshot(
        self,
        tenant_id: str,
        snapshot_id: str,
    ) -> ContextSnapshot | None:
        """Fetch snapshot ensuring tenant boundary isolation."""
        snap = self._snapshots.get(snapshot_id)
        if snap and snap.tenant_id == tenant_id:
            return snap
        return None

    def list_snapshots(
        self,
        tenant_id: str,
        user_id: str | None = None,
        limit: int = 50,
    ) -> list[ContextSnapshot]:
        """List snapshots for a tenant/user."""
        results: list[ContextSnapshot] = []
        for snap in self._snapshots.values():
            if snap.tenant_id == tenant_id:
                if user_id and snap.user_id != user_id:
                    continue
                results.append(snap)

        results.sort(key=lambda s: s.created_at, reverse=True)
        return results[:limit]

    def replay_snapshot(
        self,
        tenant_id: str,
        snapshot_id: str,
    ) -> dict[str, Any] | None:
        """Reconstruct the exact context items, quality, and explanations from a historical snapshot."""
        snap = self.get_snapshot(tenant_id, snapshot_id)
        if not snap:
            return None

        return {
            "snapshot_id": snap.snapshot_id,
            "request_id": snap.request_id,
            "created_at": snap.created_at.isoformat(),
            "environment": snap.environment,
            "total_items": len(snap.selected_items),
            "token_estimate": snap.token_estimate,
            "quality_score": snap.quality_score,
            "items": snap.selected_items,
            "retrieval_reasons": snap.retrieval_reasons,
            "missing_context": snap.missing_context,
            "conflicts": snap.conflicts,
        }
