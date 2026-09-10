"""Endpoint Model (Task 54, Prompt #39)."""

from __future__ import annotations

from app.environment.nodes import create_environment_node, generate_canonical_id
from app.environment.schemas import EnvironmentNode, NodeType, ScopeType


class EndpointModelManager:
    """Represents network service endpoints and addressable ports."""

    @staticmethod
    def create_endpoint_node(
        endpoint_id: str,
        host: str,
        port: int,
        protocol: str = "https",
        service_ref: str | None = None,
        environment: str = "PRODUCTION",
        health_status: str = "HEALTHY",
        source: str = "dns_resolver",
    ) -> EnvironmentNode:
        canonical = generate_canonical_id(NodeType.ENDPOINT, f"{protocol}://{host}:{port}", scope_id=environment)
        meta = {
            "host": host,
            "port": port,
            "protocol": protocol,
            "service_ref": service_ref,
            "environment": environment,
        }
        return create_environment_node(
            node_id=f"ep_{endpoint_id}",
            node_type=NodeType.ENDPOINT,
            canonical_id=canonical,
            display_name=f"{protocol}://{host}:{port}",
            metadata=meta,
            scope=ScopeType.NETWORK,
            scope_id=environment,
            status=health_status,
            provenance={"source": source},
            confidence=0.95,
        )
