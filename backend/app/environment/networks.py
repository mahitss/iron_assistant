"""Network Model and Network Privacy Guard (Task 54, Prompts #37, #38, #182)."""

from __future__ import annotations

from typing import Any

from app.environment.nodes import create_environment_node, generate_canonical_id
from app.environment.safety import UnauthorizedDiscoveryError
from app.environment.schemas import EnvironmentNode, NodeType, ScopeType


class NetworkModelManager:
    """Manages virtual networks, subnets, and routing topology within authorized scope."""

    @staticmethod
    def create_network_node(
        network_id: str,
        name: str,
        cidr_block: str,
        subnets: list[dict[str, Any]] | None = None,
        scope_id: str | None = None,
        is_authorized: bool = True,
        source: str = "network_telemetry",
    ) -> EnvironmentNode:
        # Prompt #38, #182: Only model authorized network observations
        if not is_authorized:
            raise UnauthorizedDiscoveryError(
                f"Network observation for '{name}' ({cidr_block}) is not authorized."
            )

        canonical = generate_canonical_id(NodeType.NETWORK, f"{name}:{cidr_block}", scope_id=scope_id)
        meta = {
            "network_name": name,
            "cidr_block": cidr_block,
            "subnets": subnets or [],
        }
        return create_environment_node(
            node_id=f"net_{network_id}",
            node_type=NodeType.NETWORK,
            canonical_id=canonical,
            display_name=f"{name} ({cidr_block})",
            metadata=meta,
            scope=ScopeType.NETWORK,
            scope_id=scope_id or network_id,
            status="ACTIVE",
            provenance={"source": source},
            confidence=0.95,
        )
