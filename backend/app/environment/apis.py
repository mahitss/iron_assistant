"""API Model and Evidence-based API Health (Task 54, Prompts #40, #41)."""

from __future__ import annotations

from app.environment.nodes import create_environment_node, generate_canonical_id
from app.environment.schemas import (
    EnvironmentNode,
    HealthEvidence,
    HealthRecord,
    NodeType,
    ScopeType,
)
from app.environment.services import ServiceModelManager


class APIModelManager:
    """Manages API specifications, contracts, auth requirements, and health evidence."""

    @staticmethod
    def create_api_node(
        api_id: str,
        name: str,
        version: str,
        service_id: str,
        endpoint_url: str,
        auth_type: str = "Bearer",  # "Bearer", "mTLS", "OAuth2", "None"
        scope_id: str | None = None,
        source: str = "openapi_spec",
    ) -> EnvironmentNode:
        canonical = generate_canonical_id(NodeType.API, f"{name}:{version}", scope_id=service_id)
        meta = {
            "api_name": name,
            "version": version,
            "service_id": service_id,
            "endpoint_url": endpoint_url,
            "auth_type": auth_type,
        }
        return create_environment_node(
            node_id=f"api_{api_id}",
            node_type=NodeType.API,
            canonical_id=canonical,
            display_name=f"{name} API ({version})",
            metadata=meta,
            scope=ScopeType.APPLICATION,
            scope_id=scope_id or service_id,
            status="ACTIVE",
            provenance={"source": source},
            confidence=0.98,
        )

    @staticmethod
    def evaluate_api_health(api_id: str, evidence: list[HealthEvidence]) -> HealthRecord:
        """Prompt #41: Use actual health evidence for API health."""
        return ServiceModelManager.evaluate_service_health(api_id, evidence)
