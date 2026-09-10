"""Container Model and Image Provenance (Task 54, Prompts #31, #32)."""

from __future__ import annotations

from app.environment.nodes import create_environment_node, generate_canonical_id
from app.environment.schemas import EnvironmentNode, NodeType, ScopeType


class ContainerModelManager:
    """Manages container runtime instances and base image provenance tracking."""

    @staticmethod
    def create_container_node(
        container_id: str,
        name: str,
        image_name: str,
        image_tag: str,
        image_digest: str,
        host_id: str,
        ports: list[str] | None = None,
        status: str = "RUNNING",
        source: str = "containerd",
    ) -> EnvironmentNode:
        canonical = generate_canonical_id(NodeType.CONTAINER, f"{host_id}:{name}:{container_id[:12]}")
        meta = {
            "container_name": name,
            "host_id": host_id,
            "image": {
                "name": image_name,
                "tag": image_tag,
                "digest": image_digest,
                "provenance_registry": image_name.split("/")[0] if "/" in image_name else "docker.io",
            },
            "ports": ports or [],
        }
        return create_environment_node(
            node_id=f"cntr_{container_id[:12]}",
            node_type=NodeType.CONTAINER,
            canonical_id=canonical,
            display_name=f"{name} ({image_name}:{image_tag})",
            metadata=meta,
            scope=ScopeType.HOST,
            scope_id=host_id,
            status=status,
            provenance={"source": source, "collector": "docker_agent"},
            confidence=0.98,
        )
