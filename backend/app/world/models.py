"""SQLAlchemy models for Kairo World Model, Environment State, and Entity Graph (Task 32)."""

import uuid
from datetime import UTC, datetime
from typing import Any, Optional

import sqlalchemy as sa
from sqlalchemy import JSON, DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


def generate_uuid(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


class WorldEntityModel(Base):
    """Authoritative or projected record of an authorized entity in the Kairo World Model."""

    __tablename__ = "world_entities"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: generate_uuid("ent"))
    type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    owner_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    project_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    source_id: Mapped[str] = mapped_column(String(256), nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    state_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    observation_type: Mapped[str] = mapped_column(String(32), default="OBSERVED", nullable=False)
    confidence: Mapped[str] = mapped_column(String(16), default="HIGH", nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    __table_args__ = (
        Index("ix_world_entities_owner_type", "owner_id", "type"),
        Index("ix_world_entities_source", "source", "source_id"),
        Index("ix_world_entities_project", "project_id"),
    )


class WorldRelationshipModel(Base):
    """Directed, typed relationship between entities in the World Model."""

    __tablename__ = "world_relationships"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: generate_uuid("rel"))
    source_entity_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    target_entity_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    relationship_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    owner_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (
        Index("ix_world_rel_source_target", "source_entity_id", "target_entity_id"),
        Index("ix_world_rel_owner", "owner_id"),
    )


class WorldObservationModel(Base):
    """Raw observation audit record attributed to a specific source system."""

    __tablename__ = "world_observations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: generate_uuid("obs"))
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    raw_observation: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    observation_type: Mapped[str] = mapped_column(String(32), nullable=False)
    confidence: Mapped[str] = mapped_column(String(16), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (
        Index("ix_world_obs_entity", "entity_id"),
    )


class WorldSnapshotModel(Base):
    """Bounded, point-in-time state snapshot for debugging, planning, and evaluation."""

    __tablename__ = "world_snapshots"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: generate_uuid("snap"))
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    project_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    snapshot_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    entities_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    relationships_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    snapshot_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (
        Index("ix_world_snapshots_user", "user_id"),
        Index("ix_world_snapshots_project", "project_id"),
    )
