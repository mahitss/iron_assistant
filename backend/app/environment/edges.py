"""EnvironmentEdge model manager, relationship validation, and anti-false topology (Task 54)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.environment.safety import EnvironmentSafetyGuard
from app.environment.schemas import EnvironmentEdge, RelationshipConfidence, RelationshipType
from app.environment.temporal import utc_now


def generate_edge_id(source: str, relationship: RelationshipType, target: str) -> str:
    """Creates deterministic edge ID."""
    return f"edge:{source}::{relationship.value}::{target}"


def create_environment_edge(
    source: str,
    relationship: RelationshipType,
    target: str,
    confidence: RelationshipConfidence = RelationshipConfidence.OBSERVED,
    provenance: dict[str, Any] | None = None,
    valid_from: datetime | None = None,
    valid_until: datetime | None = None,
    status: str = "ACTIVE",
    is_same_environment_only: bool = False,
) -> EnvironmentEdge:
    """Creates and validates an EnvironmentEdge while preventing false topology."""
    edge_id = generate_edge_id(source, relationship, target)
    now = utc_now()
    prov = provenance or {}

    # Enforce anti-false topology rules per prompt #10, #47
    EnvironmentSafetyGuard.validate_edge_topology(
        source_id=source,
        relationship=relationship.value,
        target_id=target,
        confidence=confidence.value,
        provenance=prov,
        is_same_environment_only=is_same_environment_only,
    )

    return EnvironmentEdge(
        edge_id=edge_id,
        source=source,
        relationship=relationship,
        target=target,
        confidence=confidence,
        provenance=prov,
        valid_from=valid_from or now,
        valid_until=valid_until,
        status=status,
    )
