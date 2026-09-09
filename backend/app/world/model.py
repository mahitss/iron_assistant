"""Central Kairo World Model engine facade and state coordinator (Task 32, Spec 1-4, 91-93)."""

import asyncio
from datetime import UTC, datetime, timedelta
import logging
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.events.bus import get_event_bus
from app.world.conflicts import (
    ConflictRecord,
    ConflictResolutionAction,
    StateConflictEngine,
)
from app.world.entities import (
    ConfidenceLevel,
    EntityType,
    ObservationType,
    WorldEntityCreateRequest,
    WorldEntitySchema,
    generate_entity_id,
)
from app.world.freshness import FreshnessPolicy
from app.world.models import (
    WorldEntityModel,
    WorldObservationModel,
    WorldRelationshipModel,
    WorldSnapshotModel,
)
from app.world.policies import WorldPolicyEngine
from app.world.queries import WorldQueryEngine
from app.world.registry import SourceAuthority, SourceOfTruthRegistry
from app.world.relationships import (
    RelationshipType,
    WorldRelationshipCreateRequest,
    WorldRelationshipSchema,
    generate_relationship_id,
)
from app.world.resolver import WorldContextPacket, WorldContextResolver
from app.world.snapshots import WorldSnapshotSchema, WorldSnapshotService
from app.world.state import DeviceState, StateTransitionValidator
from app.world.synchronizer import WorldSynchronizer

logger = logging.getLogger("kairo.world.model")


class KairoWorldModel:
    """The central World Model coordinating live environment state and entity graph."""

    def __init__(self) -> None:
        self._entities: dict[str, WorldEntitySchema] = {}
        self._relationships: dict[str, WorldRelationshipSchema] = {}
        self._conflicts: list[ConflictRecord] = []
        self._synchronizer = WorldSynchronizer()
        self._event_bus = get_event_bus()
        self._lock = asyncio.Lock()
        self._query_count: int = 0
        self._sync_failures: int = 0

    # --- Ingestion & Mutation ---

    async def upsert_entity(
        self,
        request: WorldEntityCreateRequest,
        owner_id: str,
        authority: SourceAuthority = SourceAuthority.AUTHORITATIVE_SYSTEM,
        session: Optional[AsyncSession] = None,
    ) -> WorldEntitySchema:
        """Declare or update an entity state with authority and conflict checks."""
        async with self._lock:
            # 1. Sanitize metadata against surveillance violations (Spec 68-72)
            clean_meta = WorldPolicyEngine.sanitize_entity_metadata(request.metadata)

            # 2. Check untrusted observation text for prompt injection (Spec 116)
            for k, v in list(clean_meta.items()):
                if isinstance(v, str):
                    _, clean_v = WorldPolicyEngine.validate_external_observation_content(v)
                    clean_meta[k] = clean_v

            ent_id = generate_entity_id(request.type, owner_id, request.source, request.source_id)
            now = datetime.now(UTC)
            expires_at = FreshnessPolicy.compute_expiration(request.type, now, request.ttl_seconds)

            existing = self._entities.get(ent_id)

            if existing:
                # Conflict evaluation (Spec 34, 35)
                conflict = StateConflictEngine.evaluate_conflict(
                    existing_entity=existing,
                    new_state=request.state,
                    new_version=request.state_version,
                    new_source=request.source,
                    new_observed_at=now,
                    new_authority=authority,
                )

                if conflict:
                    c_type, c_action, reason = conflict
                    record = ConflictRecord(
                        id=f"conf_{now.timestamp()}",
                        entity_id=ent_id,
                        conflict_type=c_type,
                        current_state=existing.state,
                        incoming_state=request.state,
                        current_source=existing.source,
                        incoming_source=request.source,
                        resolution=c_action,
                        details=reason,
                        timestamp=now,
                    )
                    self._conflicts.append(record)
                    logger.warning("Conflict detected on entity %s: %s -> %s", ent_id, c_type, c_action)

                    if c_action == ConflictResolutionAction.REJECT_UPDATE:
                        return existing

                # Valid transition checks
                if existing.type == EntityType.DEVICE:
                    if not StateTransitionValidator.can_transition_device(existing.state, request.state):
                        logger.warning("Illegal device transition rejected: %s -> %s", existing.state, request.state)
                        return existing

                existing.state = request.state
                existing.state_version = request.state_version
                existing.name = request.name
                existing.observed_at = now
                existing.expires_at = expires_at
                existing.confidence = request.confidence
                existing.observation_type = request.observation_type
                existing.metadata.update(clean_meta)
                existing.is_stale = False
                res_entity = existing
            else:
                res_entity = WorldEntitySchema(
                    id=ent_id,
                    type=request.type,
                    name=request.name,
                    owner_id=owner_id,
                    project_id=request.project_id,
                    source=request.source,
                    source_id=request.source_id,
                    state=request.state,
                    state_version=request.state_version,
                    observation_type=request.observation_type,
                    confidence=request.confidence,
                    observed_at=now,
                    expires_at=expires_at,
                    metadata=clean_meta,
                    is_stale=False,
                )
                self._entities[ent_id] = res_entity

            # Persist to database if session is present
            if session is not None:
                try:
                    stmt = select(WorldEntityModel).where(WorldEntityModel.id == ent_id)
                    db_res = await session.execute(stmt)
                    existing_db = db_res.scalar_one_or_none()
                    if existing_db:
                        existing_db.state = res_entity.state
                        existing_db.state_version = res_entity.state_version
                        existing_db.name = res_entity.name
                        existing_db.observed_at = res_entity.observed_at
                        existing_db.expires_at = res_entity.expires_at
                        existing_db.metadata_json = res_entity.metadata
                    else:
                        new_model = WorldEntityModel(
                            id=res_entity.id,
                            type=res_entity.type.value,
                            name=res_entity.name,
                            owner_id=res_entity.owner_id,
                            project_id=res_entity.project_id,
                            source=res_entity.source,
                            source_id=res_entity.source_id,
                            state=res_entity.state,
                            state_version=res_entity.state_version,
                            observation_type=res_entity.observation_type.value,
                            confidence=res_entity.confidence.value,
                            observed_at=res_entity.observed_at,
                            expires_at=res_entity.expires_at,
                            metadata_json=res_entity.metadata,
                        )
                        session.add(new_model)
                    await session.commit()
                except Exception as e:
                    logger.debug("DB persistence for entity %s skipped/failed: %s", ent_id, e)
                    try:
                        await session.rollback()
                    except Exception:
                        pass

            return res_entity

    async def add_relationship(
        self,
        request: WorldRelationshipCreateRequest,
        owner_id: str,
        session: Optional[AsyncSession] = None,
    ) -> WorldRelationshipSchema:
        """Create a typed edge between two entities."""
        async with self._lock:
            source = self._entities.get(request.source_entity_id)
            target = self._entities.get(request.target_entity_id)

            if source:
                WorldPolicyEngine.check_query_permission(owner_id, source.owner_id, source.id)
            if target:
                WorldPolicyEngine.check_query_permission(owner_id, target.owner_id, target.id)

            rel_id = generate_relationship_id(
                request.source_entity_id, request.target_entity_id, request.relationship_type
            )
            rel = WorldRelationshipSchema(
                id=rel_id,
                source_entity_id=request.source_entity_id,
                target_entity_id=request.target_entity_id,
                relationship_type=request.relationship_type,
                owner_id=owner_id,
                metadata=request.metadata,
                created_at=datetime.now(UTC),
            )
            self._relationships[rel_id] = rel

            if session is not None:
                try:
                    stmt = select(WorldRelationshipModel).where(WorldRelationshipModel.id == rel_id)
                    db_res = await session.execute(stmt)
                    if not db_res.scalar_one_or_none():
                        model = WorldRelationshipModel(
                            id=rel.id,
                            source_entity_id=rel.source_entity_id,
                            target_entity_id=rel.target_entity_id,
                            relationship_type=rel.relationship_type.value,
                            owner_id=rel.owner_id,
                            metadata_json=rel.metadata,
                            created_at=rel.created_at,
                        )
                        session.add(model)
                        await session.commit()
                except Exception as e:
                    logger.debug("DB persistence for relationship %s skipped: %s", rel_id, e)
                    try:
                        await session.rollback()
                    except Exception:
                        pass

            return rel

    # --- Event Ingest ---

    async def handle_event(self, event_type: str, payload: dict[str, Any]) -> Optional[WorldEntitySchema]:
        """Ingest events from the unified Event Bus."""
        async with self._lock:
            updated = self._synchronizer.process_event(
                event_type=event_type,
                payload=payload,
                entities_by_id=self._entities,
            )
            if updated:
                self._entities[updated.id] = updated
            return updated

    # --- Query Operations ---

    async def get_overview(self, user_id: str) -> dict[str, Any]:
        """Generate high-level environment metrics and summary (Spec 93)."""
        async with self._lock:
            self._query_count += 1
            now = datetime.now(UTC)

            # Reconcile stale statuses
            self._synchronizer.reconcile_stale_entities(list(self._entities.values()), now=now)

            user_entities = [e for e in self._entities.values() if e.owner_id == user_id]

            projects_count = len({e.id for e in user_entities if e.type == EntityType.PROJECT})
            active_tasks = len(WorldQueryEngine.get_active_tasks(user_id, None, user_entities))
            connected_devices = len(WorldQueryEngine.get_connected_devices(user_id, user_entities))

            healthy_services = 0
            degraded_services = 0
            for e in user_entities:
                if e.type == EntityType.SERVICE:
                    if e.state.upper() == "HEALTHY":
                        healthy_services += 1
                    else:
                        degraded_services += 1

            synced_repos = 0
            stale_repos = 0
            for e in user_entities:
                if e.type == EntityType.REPOSITORY:
                    if e.is_stale:
                        stale_repos += 1
                    else:
                        synced_repos += 1

            automations_count = len([e for e in user_entities if e.type == EntityType.AUTOMATION and e.state.upper() == "ACTIVE"])
            stale_total = len([e for e in user_entities if e.is_stale])

            return {
                "projects_count": projects_count,
                "active_tasks_count": active_tasks,
                "connected_devices_count": connected_devices,
                "healthy_services_count": healthy_services,
                "degraded_services_count": degraded_services,
                "synced_repos_count": synced_repos,
                "stale_repos_count": stale_repos,
                "automations_count": automations_count,
                "stale_total": stale_total,
                "conflicts_count": len(self._conflicts),
                "entities_total": len(user_entities),
            }

    async def get_project_state(self, project_id: str, user_id: str) -> dict[str, Any]:
        """Query state for a specific project."""
        async with self._lock:
            self._query_count += 1
            return WorldQueryEngine.get_project_state(
                project_id=project_id,
                user_id=user_id,
                entities=list(self._entities.values()),
                relationships=list(self._relationships.values()),
            )

    async def get_entity(self, entity_id: str, user_id: str) -> Optional[WorldEntitySchema]:
        """Fetch single entity with authorization check."""
        async with self._lock:
            self._query_count += 1
            entity = self._entities.get(entity_id)
            if entity:
                WorldPolicyEngine.check_query_permission(user_id, entity.owner_id, entity.id)
                # Compute staleness
                entity.is_stale = FreshnessPolicy.is_stale(entity.observed_at, entity.expires_at, entity.type)
                return entity
            return None

    async def get_dependencies(self, entity_id: str, user_id: str, max_depth: int = 3) -> dict[str, Any]:
        """Extract bounded dependency graph."""
        async with self._lock:
            self._query_count += 1
            return WorldQueryEngine.get_dependencies(
                entity_id=entity_id,
                user_id=user_id,
                entities_by_id=self._entities,
                relationships=list(self._relationships.values()),
                max_depth=max_depth,
            )

    async def get_changes(self, since: datetime, user_id: str, project_id: Optional[str] = None) -> list[dict[str, Any]]:
        """Query recent state changes."""
        async with self._lock:
            self._query_count += 1
            return WorldQueryEngine.get_recent_changes(
                since=since,
                user_id=user_id,
                entities=list(self._entities.values()),
                project_id=project_id,
            )

    async def build_context_packet(self, user_id: str, project_id: Optional[str] = None) -> WorldContextPacket:
        """Resolve current world context packet for Context Engine or Task Planner."""
        async with self._lock:
            return WorldContextResolver.resolve_world_context(
                user_id=user_id,
                project_id=project_id,
                entities=list(self._entities.values()),
                relationships=list(self._relationships.values()),
            )

    # --- Snapshots ---

    async def create_snapshot(
        self,
        user_id: str,
        project_id: Optional[str] = None,
        session: Optional[AsyncSession] = None,
    ) -> WorldSnapshotSchema:
        """Capture point-in-time environment snapshot."""
        async with self._lock:
            user_entities = [e for e in self._entities.values() if e.owner_id == user_id]
            if project_id:
                user_entities = [e for e in user_entities if e.project_id == project_id or e.id == project_id]
            user_relationships = [r for r in self._relationships.values() if r.owner_id == user_id]

            snap = WorldSnapshotService.create_snapshot(
                user_id=user_id,
                project_id=project_id,
                entities=user_entities,
                relationships=user_relationships,
            )
            await WorldSnapshotService.persist_snapshot(session, snap)
            return snap

    def load_snapshot(self, snapshot: WorldSnapshotSchema) -> None:
        """Load a snapshot fixture into memory (useful for testing and evaluation) (Spec 79, 137)."""
        for e in snapshot.entities:
            self._entities[e.id] = e
        for r in snapshot.relationships:
            self._relationships[r.id] = r

    # --- Health Metrics ---

    def get_health_metrics(self) -> dict[str, Any]:
        """Expose operational telemetry for World Model (Spec 91, 92)."""
        now = datetime.now(UTC)
        total = len(self._entities)
        stale_count = len([e for e in self._entities.values() if FreshnessPolicy.is_stale(e.observed_at, e.expires_at, e.type, now=now)])
        stale_pct = round((stale_count / total * 100.0) if total > 0 else 0.0, 1)

        return {
            "entity_count": total,
            "relationship_count": len(self._relationships),
            "stale_entities_count": stale_count,
            "stale_percentage": stale_pct,
            "conflicts_count": len(self._conflicts),
            "query_count": self._query_count,
            "sync_failures": self._sync_failures,
            "status": "HEALTHY" if stale_pct < 50.0 else "DEGRADED",
        }


# Module singleton
_world_model_instance: Optional[KairoWorldModel] = None


def get_world_model() -> KairoWorldModel:
    """Return application singleton of KairoWorldModel."""
    global _world_model_instance
    if _world_model_instance is None:
        _world_model_instance = KairoWorldModel()
    return _world_model_instance
