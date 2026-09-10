"""Host / Machine Model (Task 54, Prompt #16)."""

from __future__ import annotations

from app.environment.confidence import compute_confidence_score
from app.environment.nodes import create_environment_node, generate_canonical_id
from app.environment.schemas import EnvironmentNode, NodeType, ScopeType
from app.environment.temporal import calculate_freshness


class MachineModelManager:
    """Represents hosts and machines with compute, memory, storage, and network attributes."""

    @staticmethod
    def create_host_node(
        host_id: str,
        hostname: str,
        cpu_cores: int,
        memory_mb: int,
        storage_gb: int,
        os_name: str,
        ip_addresses: list[str] | None = None,
        scope_id: str | None = None,
        source: str = "host_agent",
    ) -> EnvironmentNode:
        canonical = generate_canonical_id(NodeType.HOST, host_id, scope_id=scope_id)
        meta = {
            "hostname": hostname,
            "cpu_cores": cpu_cores,
            "memory_mb": memory_mb,
            "storage_gb": storage_gb,
            "os_name": os_name,
            "ip_addresses": ip_addresses or [],
        }
        confidence = compute_confidence_score(NodeType.HOST, source, calculate_freshness(None))
        return create_environment_node(
            node_id=f"host_{host_id}",
            node_type=NodeType.HOST,
            canonical_id=canonical,
            display_name=hostname,
            metadata=meta,
            scope=ScopeType.HOST,
            scope_id=scope_id or host_id,
            status="ONLINE",
            provenance={"source": source, "collector": "host_metrics"},
            confidence=confidence,
        )
