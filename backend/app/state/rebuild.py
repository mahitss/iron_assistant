"""Side-effect-free projection rebuild coordinator (Task 39, Spec 26-28, 117-118, 142-146)."""

import asyncio
import logging
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("kairo.state.rebuild")


class ProjectionRebuildCoordinator:
    """Coordinates side-effect-free rebuilds of derived state projections with blue/green switching."""

    def __init__(self) -> None:
        self._active_rebuilds: set[str] = set()
        self._projections: dict[str, dict[str, Any]] = {}
        self._side_effects_blocked: bool = False

    @property
    def is_rebuilding(self) -> bool:
        return len(self._active_rebuilds) > 0

    @property
    def side_effects_blocked(self) -> bool:
        return self._side_effects_blocked

    async def rebuild_projection(
        self,
        projection_id: str,
        authoritative_source_fetcher: Callable[[], list[dict[str, Any]]],
        projection_mapper: Callable[[dict[str, Any]], dict[str, Any]],
    ) -> dict[str, Any]:
        """Executes a side-effect-free rebuild of the specified projection.
        
        Guarantees:
        1. Single-rebuild lock per projection ID (prevents stampedes).
        2. Side-effect suppression flag active during replay.
        3. Blue/Green atomic swap: old projection remains intact until new projection succeeds.
        4. Failure isolation: if rebuild fails, previous projection is retained.
        """
        if projection_id in self._active_rebuilds:
            raise RuntimeError(f"Rebuild already in progress for projection '{projection_id}'")

        self._active_rebuilds.add(projection_id)
        self._side_effects_blocked = True
        logger.info("Starting safe side-effect-free rebuild for projection '%s'", projection_id)

        try:
            # 1. Fetch authoritative source records
            source_records = authoritative_source_fetcher()
            
            # 2. Build new projection buffer (Green stage)
            green_buffer: dict[str, Any] = {
                "items": {},
                "rebuilt_at": datetime.now(UTC).isoformat(),
                "record_count": len(source_records),
            }

            for record in source_records:
                # Invariant: NEVER trigger external side effects during replay
                transformed = projection_mapper(record)
                item_key = transformed.get("id") or str(len(green_buffer["items"]))
                green_buffer["items"][item_key] = transformed

            # 3. Blue/Green atomic switch
            self._projections[projection_id] = green_buffer
            logger.info(
                "Projection '%s' rebuild succeeded with %d items. Swapped to active pointer.",
                projection_id,
                len(green_buffer["items"]),
            )
            return green_buffer

        except Exception as exc:
            logger.error("Projection '%s' rebuild failed: %s. Retaining previous projection.", projection_id, exc)
            raise
        finally:
            self._active_rebuilds.discard(projection_id)
            if not self._active_rebuilds:
                self._side_effects_blocked = False

    def get_projection(self, projection_id: str) -> dict[str, Any] | None:
        """Retrieves active projection data."""
        return self._projections.get(projection_id)

    def clear(self) -> None:
        self._active_rebuilds.clear()
        self._projections.clear()
        self._side_effects_blocked = False


# Global projection rebuild coordinator
rebuild_coordinator = ProjectionRebuildCoordinator()
