"""Master System State Service coordinating operational graph, snapshots, deltas, and diagnostics (Task 93).

Core principles:
- Observability and operational self-model layer only — NEVER grants permissions or overrides authority.
- Enforces EmergencyStop checks on mutating operations while allowing safe state inspections.
- Deterministic hashing, immutable snapshots, and idempotent event reduction.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
import logging
import threading
from typing import Any
import uuid

from sqlalchemy.orm import Session

from app.events.bus import get_event_bus
from app.events.schemas import Event
from app.security.emergency_stop import EmergencyStopService, get_emergency_stop_service
from app.security.exceptions import EmergencyStopActiveError
from app.system_state.db_models import (
    SystemStateDeltaModel,
    SystemStateReconciliationModel,
    SystemStateSnapshotModel,
)
from app.system_state.delta import StateDeltaEngine
from app.system_state.diagnostics import SystemDiagnosticsEngine
from app.system_state.graph import SystemStateGraph
from app.system_state.models import (
    EdgeType,
    EpistemicStatus,
    SelfModelAnswers,
    StateCategory,
    StateDelta,
    StateEdge,
    StateEntity,
    StateType,
    SystemDiagnosis,
    SystemStateSnapshot,
)
from app.system_state.reconciliation import StateReconciliationEngine
from app.system_state.reducer import SystemStateReducer
from app.system_state.self_model import SelfModelQueryEngine

logger = logging.getLogger("kairo.system_state.service")


class SystemStateService:
    """Master production-grade coordinator for Kairo's System State Graph and Self-Model."""

    def __init__(
        self,
        emergency_stop: EmergencyStopService | None = None,
        db: Session | None = None,
    ) -> None:
        self.emergency_stop = emergency_stop or get_emergency_stop_service()
        self.db = db
        self._lock = threading.RLock()

        # Core Graph & Engines
        self.graph = SystemStateGraph()
        self.reducer = SystemStateReducer(self.graph)
        self.delta_engine = StateDeltaEngine(self.graph)
        self.diagnostics_engine = SystemDiagnosticsEngine(self.graph)
        self.self_model_engine = SelfModelQueryEngine(self.graph)
        self.reconciliation_engine = StateReconciliationEngine(self.graph)

        # In-memory snapshot & delta cache
        self._latest_snapshot: SystemStateSnapshot | None = None
        self._recent_deltas: list[StateDelta] = []
        self._snapshots_history: dict[str, SystemStateSnapshot] = {}

        # Initialize default baseline system components
        self._initialize_baseline_entities()

    def _initialize_baseline_entities(self) -> None:
        """Seed initial well-known operational entities."""
        now = datetime.now(UTC)
        baseline_entities = [
            StateEntity(
                id="system:core",
                state_type=StateType.SYSTEM,
                status=StateCategory.HEALTHY,
                epistemic_status=EpistemicStatus.OBSERVED,
                health_score=1.0,
                source="bootstrap",
                metadata={"version": "0.93.0"},
            ),
            StateEntity(
                id="runtime:native_rust_runtime",
                state_type=StateType.RUNTIME,
                status=StateCategory.HEALTHY,
                epistemic_status=EpistemicStatus.OBSERVED,
                health_score=1.0,
                source="native_rust_protocol",
                ttl_seconds=60.0,
                metadata={"engine": "kairo-runtime-native"},
            ),
            StateEntity(
                id="security:emergency_stop",
                state_type=StateType.SECURITY,
                status=StateCategory.HEALTHY,
                epistemic_status=EpistemicStatus.OBSERVED,
                health_score=1.0,
                source="emergency_stop_service",
                metadata={"is_stopped": False},
            ),
            StateEntity(
                id="resource:system_resources",
                state_type=StateType.RESOURCE,
                status=StateCategory.HEALTHY,
                epistemic_status=EpistemicStatus.OBSERVED,
                health_score=0.95,
                source="resource_economy",
                metadata={"cpu_pct": 12.5, "memory_mb": 420.0},
            ),
        ]
        for ent in baseline_entities:
            self.graph.add_entity(ent)

    # --------------------------------------------------------------------------
    # Safety Checks
    # --------------------------------------------------------------------------

    def _verify_mutation_allowed(self, user_id: str | None = None) -> None:
        """Ensure EmergencyStop is not active during mutating operational state updates."""
        if self.emergency_stop.is_stopped(user_id):
            raise EmergencyStopActiveError("Emergency stop is ACTIVE. Operational state mutations are blocked.")

    def _emit_event(self, event_type: str, details: dict[str, Any]) -> None:
        """Publish canonical event to Kairo event fabric."""
        try:
            bus = get_event_bus()
            ev = Event(
                event_type=event_type,
                source="system_state_service",
                payload=details,
            )
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(bus.publish(ev))
            except RuntimeError:
                pass
        except Exception as exc:
            logger.debug("Event bus publish skipped: %s", exc)

    # --------------------------------------------------------------------------
    # Event Stream Ingestion (Phase 8)
    # --------------------------------------------------------------------------

    def process_event(
        self,
        event_type: str,
        payload: dict[str, Any],
        event_id: str | None = None,
        sequence_num: int | None = None,
        source: str = "event_bus",
        correlation_id: str | None = None,
    ) -> bool:
        """Feed a canonical event to the state reducer."""
        with self._lock:
            applied = self.reducer.reduce_event(
                event_type=event_type,
                payload=payload,
                event_id=event_id,
                sequence_num=sequence_num,
                source=source,
                correlation_id=correlation_id,
            )
            if applied and event_type.endswith((".failed", ".degraded", ".crashed", ".blocked")):
                self._emit_event(
                    "system_state.health_changed",
                    {"event_type": event_type, "source": source, "correlation_id": correlation_id},
                )
            return applied

    # --------------------------------------------------------------------------
    # Snapshot Creation & State Deltas (Phase 5, 6, 7)
    # --------------------------------------------------------------------------

    def create_snapshot(
        self,
        watermark: int | None = None,
        metadata: dict[str, Any] | None = None,
        user_id: str | None = None,
    ) -> SystemStateSnapshot:
        """Capture an immutable system state snapshot and compute delta from previous."""
        self._verify_mutation_allowed(user_id)

        with self._lock:
            snap_id = f"snap_{uuid.uuid4().hex[:12]}"
            wm = watermark if watermark is not None else self.reducer.watermark

            snapshot = self.graph.export_snapshot(
                snapshot_id=snap_id,
                watermark=wm,
                metadata=metadata or {},
            )

            # Store in-memory history
            self._snapshots_history[snap_id] = snapshot

            # Compute deltas if previous snapshot exists
            new_deltas: list[StateDelta] = []
            if self._latest_snapshot is not None:
                new_deltas = self.delta_engine.compute_deltas(self._latest_snapshot, snapshot)
                for d in new_deltas:
                    self._recent_deltas.append(d)
                # Keep recent deltas bounded
                if len(self._recent_deltas) > 500:
                    self._recent_deltas = self._recent_deltas[-500:]

            self._latest_snapshot = snapshot

            # Persist to database if session is available
            if self.db is not None:
                try:
                    entities_json = {k: v.model_dump(mode="json") for k, v in snapshot.entities.items()}
                    edges_json = [e.model_dump(mode="json") for e in snapshot.edges]

                    db_snap = SystemStateSnapshotModel(
                        snapshot_id=snapshot.snapshot_id,
                        schema_version=snapshot.schema_version,
                        system_version=snapshot.system_version,
                        source_event_watermark=snapshot.source_event_watermark,
                        state_hash=snapshot.state_hash,
                        entity_count=len(snapshot.entities),
                        edge_count=len(snapshot.edges),
                        entities_data=entities_json,
                        edges_data=edges_json,
                        metadata_json=snapshot.metadata,
                        created_at=snapshot.created_at,
                    )
                    self.db.add(db_snap)

                    for d in new_deltas:
                        db_delta = SystemStateDeltaModel(
                            delta_id=d.delta_id,
                            from_snapshot_id=d.from_snapshot_id,
                            to_snapshot_id=d.to_snapshot_id,
                            delta_type=d.delta_type.value,
                            entity_id=d.entity_id,
                            entity_type=d.entity_type.value,
                            from_status=d.from_status.value if d.from_status else None,
                            to_status=d.to_status.value if d.to_status else None,
                            epistemic_status=d.epistemic_status.value,
                            affected_tasks=d.affected_tasks,
                            affected_workflows=d.affected_workflows,
                            affected_goals=d.affected_goals,
                            affected_dependencies=d.affected_dependencies,
                            metadata_json=d.metadata,
                            detected_at=d.detected_at,
                        )
                        self.db.add(db_delta)

                    self.db.commit()
                except Exception as ex:
                    logger.warning("Database persistence for snapshot skipped or failed: %s", ex)
                    self.db.rollback()

            self._emit_event(
                "system_state.snapshot_created",
                {
                    "snapshot_id": snapshot.snapshot_id,
                    "state_hash": snapshot.state_hash,
                    "entity_count": len(snapshot.entities),
                    "edge_count": len(snapshot.edges),
                },
            )

            if new_deltas:
                self._emit_event(
                    "system_state.delta_detected",
                    {"delta_count": len(new_deltas), "snapshot_id": snap_id},
                )

            return snapshot

    # --------------------------------------------------------------------------
    # Startup & On-Demand Reconciliation (Phase 21)
    # --------------------------------------------------------------------------

    def reconcile(
        self,
        watermark_start: int = 0,
        watermark_end: int = 0,
        user_id: str | None = None,
    ) -> dict[str, Any]:
        """Execute state reconciliation against live subsystems."""
        self._verify_mutation_allowed(user_id)

        with self._lock:
            self._emit_event("system_state.reconciliation_started", {"watermark_start": watermark_start})

            res = self.reconciliation_engine.reconcile(
                latest_snapshot=self._latest_snapshot,
                watermark_start=watermark_start,
                watermark_end=watermark_end,
            )

            if self.db is not None:
                try:
                    db_rec = SystemStateReconciliationModel(
                        reconciliation_id=res["reconciliation_id"],
                        watermark_start=res["watermark_start"],
                        watermark_end=res["watermark_end"],
                        repaired_entities=res["repaired_entities"],
                        orphaned_entities=res["orphaned_entities"],
                        stale_entities=res["stale_entities"],
                        status=res["status"],
                        details=res["details"],
                    )
                    self.db.add(db_rec)
                    self.db.commit()
                except Exception as ex:
                    logger.warning("Database persistence for reconciliation failed: %s", ex)
                    self.db.rollback()

            self._emit_event("system_state.reconciliation_completed", res)
            return res

    # --------------------------------------------------------------------------
    # Observability & Self-Model Queries (Phases 16, 17, 18, 28)
    # --------------------------------------------------------------------------

    def get_summary(self) -> dict[str, Any]:
        """Generate high-level operational overview."""
        with self._lock:
            diagnosis = self.diagnostics_engine.generate_diagnosis()
            entities = self.graph.list_entities()
            edges = self.graph.list_edges()

            type_breakdown: dict[str, int] = {}
            for e in entities:
                type_breakdown[e.state_type.value] = type_breakdown.get(e.state_type.value, 0) + 1

            return {
                "system_version": "0.93.0",
                "overall_state": diagnosis.current_state.value,
                "health_score": diagnosis.health_score,
                "total_entities": len(entities),
                "total_edges": len(edges),
                "latest_snapshot_id": self._latest_snapshot.snapshot_id if self._latest_snapshot else None,
                "latest_state_hash": self._latest_snapshot.state_hash if self._latest_snapshot else None,
                "epistemic_breakdown": diagnosis.epistemic_breakdown,
                "type_breakdown": type_breakdown,
                "active_objectives_count": len(diagnosis.active_objectives),
                "active_work_count": len(diagnosis.active_work),
                "active_incidents_count": len(diagnosis.active_incidents),
                "security_emergency_stop": self.emergency_stop.is_stopped(),
            }

    def get_graph_data(self) -> dict[str, Any]:
        """Return full operational graph formatted for interactive visualization."""
        with self._lock:
            entities = self.graph.list_entities()
            edges = self.graph.list_edges()
            nodes = [
                {
                    "id": e.id,
                    "label": e.id.split(":")[-1] if ":" in e.id else e.id,
                    "type": e.state_type.value,
                    "status": e.status.value,
                    "epistemic": e.epistemic_status.value,
                    "health": e.health_score,
                    "confidence": e.confidence,
                    "source": e.source,
                    "metadata": e.metadata,
                }
                for e in entities
            ]
            links = [
                {
                    "source": edge.source_id,
                    "target": edge.target_id,
                    "type": edge.edge_type.value,
                    "epistemic": edge.epistemic_status.value,
                    "weight": edge.weight,
                }
                for edge in edges
            ]
            return {"nodes": nodes, "links": links}

    def get_diagnostics(self) -> SystemDiagnosis:
        """Produce structured self-diagnostics report."""
        with self._lock:
            return self.diagnostics_engine.generate_diagnosis()

    def get_self_model_answers(self) -> SelfModelAnswers:
        """Synthesize answers for the 13 canonical self-model questions."""
        with self._lock:
            return self.self_model_engine.answer_all(recent_deltas=self._recent_deltas)

    def get_health(self) -> dict[str, Any]:
        """Query component health and degraded elements."""
        with self._lock:
            diagnosis = self.diagnostics_engine.generate_diagnosis()
            entities = self.graph.list_entities()
            unhealthy = [
                {"id": e.id, "type": e.state_type.value, "status": e.status.value, "health": e.health_score}
                for e in entities
                if e.status != StateCategory.HEALTHY and e.status != StateCategory.ACTIVE
            ]
            return {
                "overall_state": diagnosis.current_state.value,
                "composite_health_score": diagnosis.health_score,
                "unhealthy_components": unhealthy,
            }

    def get_resources(self) -> dict[str, Any]:
        """Query resource states and pressure."""
        with self._lock:
            diagnosis = self.diagnostics_engine.generate_diagnosis()
            resources = self.graph.list_entities(state_type=StateType.RESOURCE)
            return {
                "resource_pressure": diagnosis.resource_pressure,
                "pools": [
                    {"id": r.id, "status": r.status.value, "health": r.health_score, "meta": r.metadata}
                    for r in resources
                ],
            }

    def get_dependencies(self) -> dict[str, Any]:
        """Query operational dependency states."""
        with self._lock:
            deps = self.graph.list_entities(state_type=StateType.DEPENDENCY)
            ext_deps = self.graph.list_entities(state_type=StateType.EXTERNAL_DEPENDENCY)
            return {
                "internal_dependencies": [{"id": d.id, "status": d.status.value, "meta": d.metadata} for d in deps],
                "external_dependencies": [
                    {"id": d.id, "status": d.status.value, "meta": d.metadata} for d in ext_deps
                ],
            }

    def get_incidents(self) -> dict[str, Any]:
        """Query active operational incidents and impact."""
        with self._lock:
            incidents = self.graph.list_entities(state_type=StateType.INCIDENT)
            active = [
                {
                    "incident_id": inc.id,
                    "status": inc.status.value,
                    "health": inc.health_score,
                    "meta": inc.metadata,
                    "affected_entities": [imp.id for imp in self.graph.impact_of(inc.id)],
                }
                for inc in incidents
                if inc.status not in (StateCategory.HEALTHY, StateCategory.STOPPING)
            ]
            return {"active_incidents": active, "total_recorded": len(incidents)}

    def get_recent_deltas(self, limit: int = 50) -> list[StateDelta]:
        """Return recently recorded operational state deltas."""
        with self._lock:
            return list(reversed(self._recent_deltas[-limit:]))

    def list_snapshots(self, limit: int = 20) -> list[dict[str, Any]]:
        """List historical system state snapshots."""
        with self._lock:
            snaps = list(self._snapshots_history.values())
            snaps.sort(key=lambda s: s.created_at, reverse=True)
            return [
                {
                    "snapshot_id": s.snapshot_id,
                    "created_at": s.created_at.isoformat(),
                    "state_hash": s.state_hash,
                    "entity_count": len(s.entities),
                    "edge_count": len(s.edges),
                    "schema_version": s.schema_version,
                }
                for s in snaps[:limit]
            ]

    def get_snapshot(self, snapshot_id: str) -> SystemStateSnapshot | None:
        """Fetch snapshot details by ID."""
        with self._lock:
            return self._snapshots_history.get(snapshot_id)

    # --------------------------------------------------------------------------
    # Targeted Graph Queries (Phases 10, 11, 16)
    # --------------------------------------------------------------------------

    def query_impact(self, component_id: str) -> dict[str, Any]:
        """Determine downstream impact if component_id fails or degrades."""
        with self._lock:
            impacted = self.graph.impact_of(component_id)
            affected_goals = [e.id for e in impacted if e.state_type == StateType.GOAL]
            affected_tasks = [e.id for e in impacted if e.state_type == StateType.TASK]
            affected_caps = [e.id for e in impacted if e.state_type == StateType.CAPABILITY]
            return {
                "target_component": component_id,
                "total_impacted_entities": len(impacted),
                "affected_goals": affected_goals,
                "affected_tasks": affected_tasks,
                "affected_capabilities": affected_caps,
                "all_impacted": [{"id": e.id, "type": e.state_type.value, "status": e.status.value} for e in impacted],
            }

    def query_dependents(self, component_id: str) -> dict[str, Any]:
        """Find upstream entities that depend on component_id."""
        with self._lock:
            dependents = self.graph.dependents_of(component_id)
            return {
                "target_component": component_id,
                "total_dependents": len(dependents),
                "dependents": [{"id": e.id, "type": e.state_type.value, "status": e.status.value} for e in dependents],
            }

    def query_goal(self, goal_id: str) -> dict[str, Any]:
        """Query comprehensive operational status of a goal."""
        with self._lock:
            target_id = f"goal:{goal_id}" if not goal_id.startswith("goal:") else goal_id
            goal = self.graph.get_entity(target_id)
            if not goal:
                return {"error": f"Goal '{goal_id}' not found in operational state graph"}

            resources = self.graph.resources_used_by(target_id)
            incidents = self.graph.incidents_affecting(target_id)
            blockers = self.graph.blockers_for(target_id)
            dependencies = self.graph.dependencies_of(target_id)

            return {
                "goal_id": goal.id,
                "status": goal.status.value,
                "health_score": goal.health_score,
                "epistemic_status": goal.epistemic_status.value,
                "blockers": [{"id": b.id, "status": b.status.value} for b in blockers],
                "active_incidents": [{"id": inc.id, "status": inc.status.value} for inc in incidents],
                "resources_consumed": [{"id": r.id, "status": r.status.value} for r in resources],
                "supporting_dependencies": [{"id": d.id, "type": d.state_type.value} for d in dependencies],
            }

    def query_task(self, task_id: str) -> dict[str, Any]:
        """Query comprehensive operational status of a task."""
        with self._lock:
            target_id = f"task:{task_id}" if not task_id.startswith("task:") else task_id
            task = self.graph.get_entity(target_id)
            if not task:
                return {"error": f"Task '{task_id}' not found in operational state graph"}

            serving_goals = self.graph.goals_affected_by(target_id)
            deps = self.graph.dependencies_of(target_id)

            return {
                "task_id": task.id,
                "status": task.status.value,
                "health_score": task.health_score,
                "epistemic_status": task.epistemic_status.value,
                "serving_goals": [g.id for g in serving_goals],
                "dependencies": [{"id": d.id, "type": d.state_type.value, "status": d.status.value} for d in deps],
            }


# Process-wide singleton instance
_global_system_state_service: SystemStateService | None = None


def get_system_state_service(db: Session | None = None) -> SystemStateService:
    """Retrieve or create the process-wide SystemStateService singleton."""
    global _global_system_state_service
    if _global_system_state_service is None:
        _global_system_state_service = SystemStateService(db=db)
    elif db is not None and _global_system_state_service.db is None:
        _global_system_state_service.db = db
    return _global_system_state_service
