"""Application Model (Task 54, Prompts #19, #90)."""

from __future__ import annotations

from app.environment.nodes import create_environment_node, generate_canonical_id
from app.environment.schemas import EnvironmentNode, NodeType, ScopeType


class ApplicationModelManager:
    """Represents application units, versions, and deployment environments."""

    @staticmethod
    def create_application_node(
        app_id: str,
        name: str,
        version: str,
        environment: str,
        runtime: str = "python",
        scope_id: str | None = None,
        source: str = "app_registry",
    ) -> EnvironmentNode:
        canonical = generate_canonical_id(NodeType.APPLICATION, f"{name}:{version}", scope_id=environment)
        meta = {
            "app_name": name,
            "version": version,
            "environment": environment,
            "runtime": runtime,
        }
        return create_environment_node(
            node_id=f"app_{app_id}",
            node_type=NodeType.APPLICATION,
            canonical_id=canonical,
            display_name=f"{name} (v{version})",
            metadata=meta,
            scope=ScopeType.APPLICATION,
            scope_id=scope_id or app_id,
            status="ACTIVE",
            provenance={"source": source},
            confidence=0.95,
        )
