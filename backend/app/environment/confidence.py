"""Confidence calculation and source authority modeling for Environmental Intelligence (Task 54)."""

from __future__ import annotations

from app.environment.schemas import FreshnessState, NodeType, RelationshipConfidence

# Authoritative source mappings per Prompt #76, #77
AUTHORITATIVE_SOURCES: dict[NodeType, list[str]] = {
    NodeType.REPOSITORY: ["github", "gitlab", "git", "bitbucket"],
    NodeType.CONTAINER: ["docker_daemon", "containerd", "kubernetes_api"],
    NodeType.CLUSTER: ["kubernetes_api", "cloud_eks", "cloud_gke", "cloud_aks"],
    NodeType.PROCESS: ["os_telemetry", "host_agent", "psutil", "systemd"],
    NodeType.HOST: ["host_agent", "os_telemetry", "hypervisor"],
    NodeType.DEVICE: ["device_manager", "mdm_agent", "kairo_companion"],
    NodeType.RESOURCE: ["aws_api", "gcp_api", "azure_api", "cloud_provider"],
    NodeType.DATABASE: ["db_admin_api", "cloud_rds", "cloud_spanner", "postgres_sys"],
    NodeType.SERVICE: ["service_mesh", "consul", "k8s_service", "telemetry"],
    NodeType.ENDPOINT: ["network_scanner", "dns_resolver", "load_balancer"],
}


def is_source_authoritative(node_type: NodeType, source: str) -> bool:
    """Checks if a given source is considered authoritative for the node type."""
    allowed = AUTHORITATIVE_SOURCES.get(node_type, [])
    source_lower = source.lower()
    return any(a in source_lower for a in allowed)


def compute_confidence_score(
    node_type: NodeType,
    source: str,
    freshness: FreshnessState,
    is_verified: bool = False,
    inferred: bool = False,
) -> float:
    """Calculates confidence score [0.0 - 1.0] based on authority, freshness, and verification."""
    if inferred:
        base = 0.45
    elif is_source_authoritative(node_type, source):
        base = 0.95
    else:
        base = 0.75

    if is_verified:
        base = min(1.0, base + 0.1)

    # Penalize stale/expired observations
    if freshness == FreshnessState.STALE:
        base *= 0.8
    elif freshness == FreshnessState.EXPIRED:
        base *= 0.4
    elif freshness == FreshnessState.UNKNOWN:
        base *= 0.5

    return round(max(0.0, min(1.0, base)), 2)


def map_relationship_confidence(confidence_str: str) -> RelationshipConfidence:
    """Safely normalizes relationship confidence enum."""
    val = confidence_str.upper()
    try:
        return RelationshipConfidence(val)
    except ValueError:
        return RelationshipConfidence.UNKNOWN
