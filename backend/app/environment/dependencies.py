"""Dependency Graph, dependency classification, and authority validation (Task 54, Prompts #44-#50)."""

from __future__ import annotations

from typing import Any

from app.environment.edges import create_environment_edge
from app.environment.schemas import DependencyType, EnvironmentEdge, RelationshipConfidence, RelationshipType


class DependencyManager:
    """Classifies and verifies structural dependencies across services, datastores, and systems."""

    @staticmethod
    def create_dependency(
        source_id: str,
        target_id: str,
        dependency_type: DependencyType,
        is_runtime_blocking: bool = True,
        confidence: RelationshipConfidence = RelationshipConfidence.OBSERVED,
        provenance: dict[str, Any] | None = None,
    ) -> EnvironmentEdge:
        prov = provenance or {"source": "telemetry", "dependency_type": dependency_type.value}
        prov["is_runtime_blocking"] = is_runtime_blocking
        prov["dependency_category"] = dependency_type.value

        # Map dependency category to edge relationship
        rel = RelationshipType.DEPENDS_ON
        if dependency_type == DependencyType.DATA:
            rel = RelationshipType.READS_FROM
        elif dependency_type == DependencyType.NETWORK:
            rel = RelationshipType.CONNECTS_TO
        elif dependency_type == DependencyType.CONFIGURATION:
            rel = RelationshipType.CONFIGURED_BY
        elif dependency_type == DependencyType.AUTH:
            rel = RelationshipType.PROTECTED_BY
        elif dependency_type == DependencyType.BUILD:
            rel = RelationshipType.BUILT_FROM
        elif dependency_type == DependencyType.DEPLOYMENT:
            rel = RelationshipType.DEPLOYS_TO

        return create_environment_edge(
            source=source_id,
            relationship=rel,
            target=target_id,
            confidence=confidence,
            provenance=prov,
        )
