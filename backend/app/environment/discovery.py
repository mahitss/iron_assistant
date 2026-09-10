"""Discovery Orchestrator and Unknown Resource Handling (Task 54, Prompts #86-#92)."""

from __future__ import annotations

from typing import Any

from app.environment.nodes import create_environment_node, generate_canonical_id
from app.environment.safety import UnauthorizedDiscoveryError
from app.environment.schemas import EnvironmentNode, NodeType, ScopeType


class DiscoveryEngine:
    """Coordinates authorized environmental discovery across adapters."""

    @staticmethod
    def register_discovered_resource(
        node_type: NodeType,
        identifier: str,
        display_name: str,
        metadata: dict[str, Any],
        scope: ScopeType = ScopeType.SYSTEM,
        scope_id: str | None = None,
        is_authorized_scope: bool = True,
        source: str = "auto_discovery",
    ) -> EnvironmentNode:
        # Prompt #86-#90: Use authorized discovery
        if not is_authorized_scope:
            raise UnauthorizedDiscoveryError(
                f"Discovery failed: target resource '{identifier}' is outside authorized scope {scope.value} ({scope_id})."
            )

        canonical = generate_canonical_id(node_type, identifier, scope_id=scope_id)
        return create_environment_node(
            node_id=f"disc_{node_type.value.lower()}_{identifier.replace('/', '_')[:16]}",
            node_type=node_type,
            canonical_id=canonical,
            display_name=display_name,
            metadata=metadata,
            scope=scope,
            scope_id=scope_id,
            status="ACTIVE",
            provenance={"source": source, "authorized": True},
            confidence=0.90,
        )

    @staticmethod
    def register_unknown_resource(
        raw_identifier: str,
        observed_network_location: str,
        evidence: dict[str, Any],
    ) -> EnvironmentNode:
        """Prompt #91, #92: Represent unknown resource separately. Unknown != Safe; requires caution."""
        canonical = generate_canonical_id(NodeType.RESOURCE, f"unknown:{raw_identifier}")
        meta = {
            "is_unrecognized": True,
            "caution_level": "HIGH",  # Prompt #92: Unknown != Safe
            "network_location": observed_network_location,
            "evidence": evidence,
        }
        return create_environment_node(
            node_id=f"unk_{raw_identifier[:12]}",
            node_type=NodeType.RESOURCE,
            canonical_id=canonical,
            display_name=f"UNKNOWN RESOURCE ({raw_identifier})",
            metadata=meta,
            scope=ScopeType.NETWORK,
            status="UNKNOWN",
            provenance={"source": "passive_network_sniffer", "caution": "unverified_unregistered"},
            confidence=0.30,
        )
