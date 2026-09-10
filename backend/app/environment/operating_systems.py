"""Operating System metadata modeling (Task 54, Prompt #16)."""

from __future__ import annotations

from app.environment.nodes import create_environment_node, generate_canonical_id
from app.environment.schemas import EnvironmentNode, NodeType, ScopeType


class OperatingSystemModelManager:
    """Models operating system state and patch levels."""

    @staticmethod
    def create_os_node(
        os_id: str,
        os_family: str,  # Linux, Windows, macOS
        version: str,
        kernel: str,
        patch_level: str | None = None,
        scope_id: str | None = None,
        source: str = "os_telemetry",
    ) -> EnvironmentNode:
        canonical = generate_canonical_id(NodeType.RESOURCE, f"os_{os_id}", scope_id=scope_id)
        meta = {
            "os_family": os_family,
            "version": version,
            "kernel": kernel,
            "patch_level": patch_level or "unknown",
        }
        return create_environment_node(
            node_id=f"os_{os_id}",
            node_type=NodeType.RESOURCE,
            canonical_id=canonical,
            display_name=f"{os_family} {version}",
            metadata=meta,
            scope=ScopeType.HOST,
            scope_id=scope_id,
            status="ACTIVE",
            provenance={"source": source},
            confidence=0.95,
        )
