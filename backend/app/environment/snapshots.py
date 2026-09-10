"""Environment Snapshots and As-Of Historical State Reconstruction (Task 54, Prompts #66-#73, #206, #207)."""

from __future__ import annotations

import uuid
from datetime import datetime

from app.environment.schemas import DigitalTwin, EnvironmentSnapshot
from app.environment.temporal import assert_no_future_leakage, calculate_freshness, parse_utc, utc_now


class SnapshotManager:
    """Creates point-in-time snapshots and reconstructs historical as-of environments without future leakage."""

    @staticmethod
    def create_snapshot(twin: DigitalTwin) -> EnvironmentSnapshot:
        """Serializes current twin state into an immutable snapshot."""
        now = utc_now()
        sid = f"snap_{twin.scope.value.lower()}_{uuid.uuid4().hex[:8]}"
        freshness = calculate_freshness(twin.timestamp)

        return EnvironmentSnapshot(
            snapshot_id=sid,
            scope=twin.scope,
            scope_id=twin.scope_id,
            version=twin.version,
            timestamp=twin.timestamp,
            nodes=[n.model_dump() for n in twin.nodes.values()],
            edges=[e.model_dump() for e in twin.edges.values()],
            health_summary={k: v.model_dump() for k, v in twin.health.items()},
            freshness=freshness,
            created_at=now,
        )

    @staticmethod
    def reconstruct_as_of(
        snapshots: list[EnvironmentSnapshot],
        as_of_time: datetime | str,
    ) -> EnvironmentSnapshot | None:
        """Prompt #67, #68, #69: Reconstructs state at timestamp. Forbids future leakage."""
        target_dt = parse_utc(as_of_time)
        valid_candidates = []

        for s in snapshots:
            s_dt = parse_utc(s.timestamp)
            if s_dt <= target_dt:
                valid_candidates.append((s_dt, s))

        if not valid_candidates:
            return None

        # Sort by timestamp descending to pick most recent snapshot before or at as_of_time
        valid_candidates.sort(key=lambda x: x[0], reverse=True)
        chosen = valid_candidates[0][1]

        # Verify no future leakage
        assert_no_future_leakage(target_dt, chosen.timestamp)
        return chosen
