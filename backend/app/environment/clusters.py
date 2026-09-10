"""Cluster Model (Task 54, Prompt #33)."""

from __future__ import annotations

from app.environment.nodes import create_environment_node, generate_canonical_id
from app.environment.schemas import EnvironmentNode, NodeType, ScopeType


class ClusterModelManager:
    """Manages container orchestrator clusters (Kubernetes, ECS, Nomad)."""

    @staticmethod
    def create_cluster_node(
        cluster_id: str,
        name: str,
        cluster_type: str = "kubernetes",
        version: str = "1.28",
        node_count: int = 3,
        namespaces: list[str] | None = None,
        health: str = "HEALTHY",
        scope_id: str | None = None,
        source: str = "kubernetes_api",
    ) -> EnvironmentNode:
        canonical = generate_canonical_id(NodeType.CLUSTER, f"{cluster_type}:{name}", scope_id=scope_id)
        meta = {
            "cluster_name": name,
            "cluster_type": cluster_type,
            "version": version,
            "node_count": node_count,
            "namespaces": namespaces or ["default"],
            "health": health,
        }
        return create_environment_node(
            node_id=f"cls_{cluster_id}",
            node_type=NodeType.CLUSTER,
            canonical_id=canonical,
            display_name=f"{name} ({cluster_type})",
            metadata=meta,
            scope=ScopeType.CLOUD,
            scope_id=scope_id or cluster_id,
            status=health,
            provenance={"source": source, "collector": "k8s_operator"},
            confidence=0.98,
        )
