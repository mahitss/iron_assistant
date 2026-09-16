"""Startup Reconciliation and Orphaned State Repair Engine (Task 93 Phase 21).

Enforces:
- Never blindly trust a persisted snapshot after restart.
- Discovers state drift between authoritative subsystems and persisted representations.
- Reconciles orphaned tasks, stale capabilities, and missing heartbeats.
"""

from __future__ import annotations

from datetime import UTC, datetime
import logging
from typing import TYPE_CHECKING, Any
import uuid

from app.security.emergency_stop import get_emergency_stop_service
from app.system_state.models import (
    EpistemicStatus,
    StateCategory,
    StateEntity,
    StateType,
)

if TYPE_CHECKING:
    from app.system_state.graph import SystemStateGraph
    from app.system_state.models import SystemStateSnapshot

logger = logging.getLogger("kairo.system_state.reconciliation")


class StateReconciliationEngine:
    """Reconciles persisted state against live authoritative subsystems upon startup or demand."""

    def __init__(self, graph: SystemStateGraph) -> None:
        self._graph = graph
        self._emergency_stop = get_emergency_stop_service()

    def reconcile(
        self,
        latest_snapshot: SystemStateSnapshot | None = None,
        watermark_start: int = 0,
        watermark_end: int = 0,
    ) -> dict[str, Any]:
        """Perform reconciliation of the state graph against live subsystems."""
        now = datetime.now(UTC)
        rec_id = f"rec_{uuid.uuid4().hex[:12]}"
        logger.info("Initiating system state reconciliation (id=%s)...", rec_id)

        repaired_count = 0
        orphaned_count = 0
        stale_count = 0
        details: dict[str, Any] = {"actions": []}

        # 1. Restore from snapshot if graph is empty and snapshot is available
        if latest_snapshot and len(self._graph.list_entities()) == 0:
            for entity in latest_snapshot.entities.values():
                # Invariant: On restart, active executions cannot be blindly trusted as active
                if entity.state_type in (StateType.TASK, StateType.WORKFLOW) and entity.status == StateCategory.ACTIVE:
                    recovered_entity = entity.with_update(
                        status=StateCategory.UNKNOWN,
                        epistemic_status=EpistemicStatus.UNKNOWN,
                        confidence=0.3,
                        metadata={"restored_from_snapshot": latest_snapshot.snapshot_id},
                    )
                    self._graph.add_entity(recovered_entity)
                    orphaned_count += 1
                    details["actions"].append(f"Marked unverified active work {entity.id} as UNKNOWN on restart")
                else:
                    self._graph.add_entity(entity)

            for edge in latest_snapshot.edges:
                self._graph.add_edge(edge)

        # 2. Check EmergencyStop authority (absolute constraint)
        is_stopped = self._emergency_stop.is_stopped()
        stop_entity = StateEntity(
            id="security:emergency_stop",
            state_type=StateType.SECURITY,
            status=StateCategory.BLOCKED if is_stopped else StateCategory.HEALTHY,
            epistemic_status=EpistemicStatus.OBSERVED,
            health_score=0.0 if is_stopped else 1.0,
            source="emergency_stop_service",
            metadata={"is_stopped": is_stopped, "reconciled_at": now.isoformat()},
        )
        self._graph.add_entity(stop_entity)
        repaired_count += 1

        # 3. Detect and mark stale entities
        stale_entities = self._graph.mark_stale_entities(now=now)
        stale_count = len(stale_entities)
        if stale_count > 0:
            details["actions"].append(f"Identified and updated {stale_count} stale/unverified entities")

        # 4. Reconcile native runtime state (must not assume healthy without live heartbeat)
        native_runtime = self._graph.get_entity("runtime:native_rust_runtime")
        if native_runtime and native_runtime.is_stale(now):
            updated_runtime = native_runtime.with_update(
                status=StateCategory.UNKNOWN,
                epistemic_status=EpistemicStatus.UNKNOWN,
                confidence=0.1,
                metadata={"reason": "Missing heartbeat post-restart"},
            )
            self._graph.add_entity(updated_runtime)
            repaired_count += 1
            details["actions"].append("Transitioned native runtime to UNKNOWN due to missing heartbeat")

        logger.info(
            "System state reconciliation complete: repaired=%d, orphaned=%d, stale=%d",
            repaired_count,
            orphaned_count,
            stale_count,
        )

        return {
            "reconciliation_id": rec_id,
            "status": "COMPLETED",
            "watermark_start": watermark_start,
            "watermark_end": watermark_end,
            "repaired_entities": repaired_count,
            "orphaned_entities": orphaned_count,
            "stale_entities": stale_count,
            "details": details,
            "completed_at": now.isoformat(),
        }
