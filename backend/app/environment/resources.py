"""Generic Resource Model and Allocation Tracking (Task 54)."""

from __future__ import annotations

from typing import Any

from app.environment.nodes import create_environment_node, generate_canonical_id
from app.environment.schemas import EnvironmentNode, NodeType, ScopeType


class ResourceManager:
    """Manages generic resources and allocation descriptors."""

    @staticmethod
    def create_resource_node(
        resource_id: str,
        name: str,
        resource_kind: str,
        allocated_to: str | None = None,
        properties: dict[str, Any] | None = None,
        scope_id: str | None = None,
        source: str = "resource_allocator",
    ) -> EnvironmentNode:
        canonical = generate_canonical_id(NodeType.RESOURCE, f"{resource_kind}:{name}", scope_id=scope_id)
        meta = {
            "resource_kind": resource_kind,
            "allocated_to": allocated_to,
            "properties": properties or {},
        }
        return create_environment_node(
            node_id=f"res_{resource_id}",
            node_type=NodeType.RESOURCE,
            canonical_id=canonical,
            display_name=f"{name} ({resource_kind})",
            metadata=meta,
            scope=ScopeType.SYSTEM,
            scope_id=scope_id,
            status="ALLOCATED" if allocated_to else "AVAILABLE",
            provenance={"source": source},
            confidence=0.95,
        )
