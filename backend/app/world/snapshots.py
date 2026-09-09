"""Point-in-time world snapshots, serialization, and test fixture loading (Task 32, Spec 36, 37, 77-80, 137)."""

from datetime import UTC, datetime
import hashlib
import json
import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.world.entities import (
    ConfidenceLevel,
    EntityType,
    ObservationType,
    WorldEntitySchema,
)
from app.world.models import WorldSnapshotModel
from app.world.relationships import RelationshipType, WorldRelationshipSchema

logger = logging.getLogger("kairo.world.snapshots")


class WorldSnapshotSchema(BaseModel):
    """Point-in-time immutable snapshot of an environment state (Spec 36)."""

    id: str = Field(description="Unique snapshot identifier")
    user_id: str = Field(description="Owner tenant identifier")
    project_id: Optional[str] = Field(default=None, description="Project scope")
    snapshot_hash: str = Field(description="SHA-256 hash of snapshot content")
    entities: list[WorldEntitySchema] = Field(default_factory=list, description="Bounded entity list")
    relationships: list[WorldRelationshipSchema] = Field(default_factory=list, description="Bounded relationship graph")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class WorldSnapshotService:
    """Manages creation, serialization, and loading of bounded world snapshots."""

    MAX_ENTITIES_PER_SNAPSHOT: int = 500  # Strict ceiling to prevent memory bloating (Spec 37)

    @classmethod
    def create_snapshot(
        cls,
        user_id: str,
        project_id: Optional[str],
        entities: list[WorldEntitySchema],
        relationships: list[WorldRelationshipSchema],
    ) -> WorldSnapshotSchema:
        """Create an in-memory bounded snapshot object with SHA-256 integrity hash."""
        # Bound entities and relationships
        bounded_entities = entities[: cls.MAX_ENTITIES_PER_SNAPSHOT]
        bounded_relationships = relationships[: cls.MAX_ENTITIES_PER_SNAPSHOT * 2]

        # Compute deterministic content hash
        hash_payload = {
            "user_id": user_id,
            "project_id": project_id,
            "entities": [e.id for e in bounded_entities],
            "relationships": [f"{r.source_entity_id}->{r.target_entity_id}" for r in bounded_relationships],
        }
        digest = hashlib.sha256(json.dumps(hash_payload, sort_keys=True).encode("utf-8")).hexdigest()

        return WorldSnapshotSchema(
            id=f"snap_{digest[:16]}",
            user_id=user_id,
            project_id=project_id,
            snapshot_hash=digest,
            entities=bounded_entities,
            relationships=bounded_relationships,
            created_at=datetime.now(UTC),
        )

    @classmethod
    async def persist_snapshot(
        cls,
        session: Optional[AsyncSession],
        snapshot: WorldSnapshotSchema,
    ) -> str:
        """Persist snapshot to database if session is available."""
        if session is not None:
            model = WorldSnapshotModel(
                id=snapshot.id,
                user_id=snapshot.user_id,
                project_id=snapshot.project_id,
                snapshot_hash=snapshot.snapshot_hash,
                entities_count=len(snapshot.entities),
                relationships_count=len(snapshot.relationships),
                snapshot_data=snapshot.model_dump(mode="json"),
                created_at=snapshot.created_at,
            )
            session.add(model)
            await session.commit()
            return model.id
        return snapshot.id

    @classmethod
    def create_synthetic_test_world(cls, user_id: str = "test_user", project_id: str = "proj_alpha") -> WorldSnapshotSchema:
        """Create a deterministic synthetic environment fixture (Spec 78, 137)."""
        now = datetime.now(UTC)

        project_ent = WorldEntitySchema(
            id="ent_proj_alpha",
            type=EntityType.PROJECT,
            name="Project Alpha",
            owner_id=user_id,
            project_id=project_id,
            source="projects",
            source_id=project_id,
            state="ACTIVE",
            observed_at=now,
            metadata={"description": "Test environment project"},
        )

        repo_ent = WorldEntitySchema(
            id="ent_repo_alpha",
            type=EntityType.REPOSITORY,
            name="kairo-core",
            owner_id=user_id,
            project_id=project_id,
            source="github",
            source_id="repo_12345",
            state="SYNCED",
            observed_at=now,
            metadata={"default_branch": "main", "ci_status": "FAILED", "head_commit": "abc1234"},
        )

        branch_ent = WorldEntitySchema(
            id="ent_branch_main",
            type=EntityType.BRANCH,
            name="main",
            owner_id=user_id,
            project_id=project_id,
            source="github",
            source_id="branch_main",
            state="SYNCED",
            observed_at=now,
            metadata={"head_commit": "abc1234"},
        )

        device_ent = WorldEntitySchema(
            id="ent_dev_pc",
            type=EntityType.DEVICE,
            name="Dev-PC",
            owner_id=user_id,
            project_id=None,
            source="local_companion",
            source_id="dev_001",
            state="CONNECTED",
            observed_at=now,
            metadata={"platform": "windows", "companion_version": "1.1.0"},
        )

        service_ent = WorldEntitySchema(
            id="ent_service_api",
            type=EntityType.SERVICE,
            name="backend-api",
            owner_id=user_id,
            project_id=project_id,
            source="observability",
            source_id="svc_api",
            state="HEALTHY",
            observed_at=now,
            metadata={"environment": "development", "version": "1.1.0"},
        )

        db_service_ent = WorldEntitySchema(
            id="ent_service_db",
            type=EntityType.SERVICE,
            name="database",
            owner_id=user_id,
            project_id=project_id,
            source="observability",
            source_id="svc_db",
            state="HEALTHY",
            observed_at=now,
            metadata={"environment": "development", "engine": "postgresql"},
        )

        entities = [project_ent, repo_ent, branch_ent, device_ent, service_ent, db_service_ent]

        # Relationships
        rel1 = WorldRelationshipSchema(
            id="rel_proj_repo",
            source_entity_id=project_ent.id,
            target_entity_id=repo_ent.id,
            relationship_type=RelationshipType.CONTAINS,
            owner_id=user_id,
        )
        rel2 = WorldRelationshipSchema(
            id="rel_repo_branch",
            source_entity_id=repo_ent.id,
            target_entity_id=branch_ent.id,
            relationship_type=RelationshipType.CONTAINS,
            owner_id=user_id,
        )
        rel3 = WorldRelationshipSchema(
            id="rel_svc_db",
            source_entity_id=service_ent.id,
            target_entity_id=db_service_ent.id,
            relationship_type=RelationshipType.DEPENDS_ON,
            owner_id=user_id,
        )

        return cls.create_snapshot(
            user_id=user_id,
            project_id=project_id,
            entities=entities,
            relationships=[rel1, rel2, rel3],
        )
