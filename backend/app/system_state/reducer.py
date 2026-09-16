"""Idempotent event-sourced state reducer (Task 93 Phase 8).

Consumes canonical system events and applies deterministic state mutations
to the operational state graph while enforcing epistemic integrity and replay safety.
"""

from __future__ import annotations

from collections import OrderedDict
from datetime import UTC, datetime
import logging
from typing import Any

from app.system_state.graph import SystemStateGraph
from app.system_state.models import (
    EdgeType,
    EpistemicStatus,
    StateCategory,
    StateEdge,
    StateEntity,
    StateType,
)

logger = logging.getLogger("kairo.system_state.reducer")


class SystemStateReducer:
    """Idempotent state reducer transforming event streams into operational state graph updates."""

    def __init__(self, graph: SystemStateGraph, max_history: int = 10000) -> None:
        self._graph = graph
        self._processed_events: OrderedDict[str, int] = OrderedDict()
        self._max_history = max_history
        self._watermark: int = 0

    @property
    def watermark(self) -> int:
        return self._watermark

    def is_processed(self, event_id: str) -> bool:
        """Check if an event ID has already been applied."""
        return event_id in self._processed_events

    def reduce_event(
        self,
        event_type: str,
        payload: dict[str, Any],
        event_id: str | None = None,
        sequence_num: int | None = None,
        source: str = "event_bus",
        correlation_id: str | None = None,
    ) -> bool:
        """Apply an operational event idempotently to the state graph."""
        if not event_type or not isinstance(payload, dict):
            logger.warning("Rejected invalid event: %s", event_type)
            return False

        # Deduplication check
        if event_id:
            if event_id in self._processed_events:
                logger.debug("Skipping duplicate event: %s (%s)", event_type, event_id)
                return False
            self._processed_events[event_id] = sequence_num or 0
            if len(self._processed_events) > self._max_history:
                self._processed_events.popitem(last=False)

        if sequence_num and sequence_num > self._watermark:
            self._watermark = sequence_num

        try:
            self._dispatch_event(event_type, payload, source, correlation_id)
            return True
        except Exception as ex:
            logger.exception("Failed to reduce event %s: %s", event_type, ex)
            return False

    def _dispatch_event(
        self, event_type: str, payload: dict[str, Any], source: str, correlation_id: str | None
    ) -> None:
        now = datetime.now(UTC)

        # ---------------------------------------------------------
        # Tasks & Workflows (Phase 10)
        # ---------------------------------------------------------
        if event_type in ("tasks.started", "task.started"):
            task_id = payload.get("task_id", payload.get("id"))
            if task_id:
                entity = StateEntity(
                    id=f"task:{task_id}",
                    state_type=StateType.TASK,
                    status=StateCategory.ACTIVE,
                    epistemic_status=EpistemicStatus.OBSERVED,
                    confidence=1.0,
                    source=source,
                    correlation_id=correlation_id,
                    observed_at=now,
                    updated_at=now,
                    metadata=payload,
                )
                self._graph.add_entity(entity)

                # Link to goal if present
                goal_id = payload.get("goal_id")
                if goal_id:
                    self._graph.add_edge(
                        StateEdge(
                            source_id=f"goal:{goal_id}",
                            target_id=f"task:{task_id}",
                            edge_type=EdgeType.GOAL_TASK,
                        )
                    )

        elif event_type in ("tasks.completed", "task.completed"):
            task_id = payload.get("task_id", payload.get("id"))
            if task_id:
                existing = self._graph.get_entity(f"task:{task_id}")
                if existing:
                    self._graph.add_entity(
                        existing.with_update(status=StateCategory.HEALTHY, health_score=1.0, metadata=payload)
                    )

        elif event_type in ("tasks.failed", "task.failed"):
            task_id = payload.get("task_id", payload.get("id"))
            if task_id:
                existing = self._graph.get_entity(f"task:{task_id}")
                if existing:
                    self._graph.add_entity(
                        existing.with_update(status=StateCategory.FAILED, health_score=0.0, metadata=payload)
                    )

        elif event_type in ("workflow.started", "workflows.started"):
            wf_id = payload.get("workflow_id", payload.get("id"))
            if wf_id:
                self._graph.add_entity(
                    StateEntity(
                        id=f"workflow:{wf_id}",
                        state_type=StateType.WORKFLOW,
                        status=StateCategory.ACTIVE,
                        epistemic_status=EpistemicStatus.OBSERVED,
                        source=source,
                        correlation_id=correlation_id,
                        metadata=payload,
                    )
                )

        # ---------------------------------------------------------
        # Capabilities (Phase 25)
        # ---------------------------------------------------------
        elif event_type.startswith("capability.") or event_type.startswith("capabilities."):
            cap_id = payload.get("capability_id", payload.get("id"))
            status_str = payload.get("lifecycle_state", payload.get("status", "ACTIVE")).upper()
            status = getattr(StateCategory, status_str, StateCategory.ACTIVE)
            if cap_id:
                existing = self._graph.get_entity(f"cap:{cap_id}")
                if existing:
                    self._graph.add_entity(existing.with_update(status=status, metadata=payload))
                else:
                    self._graph.add_entity(
                        StateEntity(
                            id=f"cap:{cap_id}",
                            state_type=StateType.CAPABILITY,
                            status=status,
                            epistemic_status=EpistemicStatus.OBSERVED,
                            source=source,
                            metadata=payload,
                        )
                    )

        # ---------------------------------------------------------
        # Native Rust Runtime & Components (Phase 9)
        # ---------------------------------------------------------
        elif event_type in ("native.runtime.heartbeat", "runtime.heartbeat"):
            runtime_id = payload.get("runtime_id", "native_rust_runtime")
            health = float(payload.get("health_score", 1.0))
            status = StateCategory.HEALTHY if health >= 0.8 else StateCategory.DEGRADED
            self._graph.add_entity(
                StateEntity(
                    id=f"runtime:{runtime_id}",
                    state_type=StateType.RUNTIME,
                    status=status,
                    epistemic_status=EpistemicStatus.OBSERVED,
                    health_score=health,
                    ttl_seconds=30.0,  # Strict heartbeat freshness
                    source="native_rust_protocol",
                    metadata=payload,
                )
            )

        elif event_type in ("native.runtime.crashed", "runtime.crashed"):
            runtime_id = payload.get("runtime_id", "native_rust_runtime")
            self._graph.add_entity(
                StateEntity(
                    id=f"runtime:{runtime_id}",
                    state_type=StateType.RUNTIME,
                    status=StateCategory.FAILED,
                    epistemic_status=EpistemicStatus.OBSERVED,
                    health_score=0.0,
                    source="supervisor",
                    metadata=payload,
                )
            )

        # ---------------------------------------------------------
        # Goals & Strategic Objectives (Phase 11)
        # ---------------------------------------------------------
        elif event_type in ("goals.created", "goal.created", "goal.updated"):
            goal_id = payload.get("goal_id", payload.get("id"))
            if goal_id:
                self._graph.add_entity(
                    StateEntity(
                        id=f"goal:{goal_id}",
                        state_type=StateType.GOAL,
                        status=StateCategory.ACTIVE,
                        epistemic_status=EpistemicStatus.OBSERVED,
                        source=source,
                        metadata=payload,
                    )
                )

        elif event_type in ("goal.blocked", "goals.blocked"):
            goal_id = payload.get("goal_id", payload.get("id"))
            if goal_id:
                existing = self._graph.get_entity(f"goal:{goal_id}")
                if existing:
                    self._graph.add_entity(
                        existing.with_update(status=StateCategory.BLOCKED, health_score=0.3, metadata=payload)
                    )

        # ---------------------------------------------------------
        # Resource Economy (Phase 12)
        # ---------------------------------------------------------
        elif event_type.startswith("resource.") or event_type.startswith("resources."):
            res_id = payload.get("resource_id", payload.get("pool_id", "system_resources"))
            is_exhausted = payload.get("exhausted", False)
            status = StateCategory.DEGRADED if is_exhausted else StateCategory.HEALTHY
            self._graph.add_entity(
                StateEntity(
                    id=f"resource:{res_id}",
                    state_type=StateType.RESOURCE,
                    status=status,
                    epistemic_status=EpistemicStatus.OBSERVED,
                    health_score=0.2 if is_exhausted else 0.95,
                    source="resource_economy",
                    metadata=payload,
                )
            )

        # ---------------------------------------------------------
        # SecurityCenter & EmergencyStop (Phase 13 & 32)
        # ---------------------------------------------------------
        elif event_type in ("security.emergency_stop.triggered", "emergency_stop.activated"):
            self._graph.add_entity(
                StateEntity(
                    id="security:emergency_stop",
                    state_type=StateType.SECURITY,
                    status=StateCategory.BLOCKED,
                    epistemic_status=EpistemicStatus.OBSERVED,
                    health_score=0.0,
                    source="security_center",
                    metadata=payload,
                )
            )

        elif event_type in ("security.emergency_stop.reset", "emergency_stop.reset"):
            self._graph.add_entity(
                StateEntity(
                    id="security:emergency_stop",
                    state_type=StateType.SECURITY,
                    status=StateCategory.HEALTHY,
                    epistemic_status=EpistemicStatus.OBSERVED,
                    health_score=1.0,
                    source="security_center",
                    metadata=payload,
                )
            )

        # ---------------------------------------------------------
        # Incidents & Recoveries (Phase 15)
        # ---------------------------------------------------------
        elif event_type.startswith("incident.") or event_type.startswith("reliability.incident"):
            inc_id = payload.get("incident_id", payload.get("id"))
            is_resolved = payload.get("resolved", False)
            status = StateCategory.HEALTHY if is_resolved else StateCategory.FAILED
            if inc_id:
                self._graph.add_entity(
                    StateEntity(
                        id=f"incident:{inc_id}",
                        state_type=StateType.INCIDENT,
                        status=status,
                        epistemic_status=EpistemicStatus.OBSERVED,
                        health_score=1.0 if is_resolved else 0.0,
                        source="reliability_engine",
                        metadata=payload,
                    )
                )

        # ---------------------------------------------------------
        # Simulations / Digital Twin (Phase 22 - Rigid Epistemic Boundary)
        # ---------------------------------------------------------
        elif event_type.startswith("simulation."):
            sim_id = payload.get("simulation_id", "twin_run")
            # NON-NEGOTIABLE INVARIANT: Simulation state is PREDICTED, NEVER ACTUAL FACT
            self._graph.add_entity(
                StateEntity(
                    id=f"sim:{sim_id}",
                    state_type=StateType.COMPONENT,
                    status=StateCategory.SIMULATING,
                    epistemic_status=EpistemicStatus.PREDICTED,
                    confidence=float(payload.get("confidence", 0.7)),
                    source="digital_twin",
                    metadata=payload,
                )
            )
