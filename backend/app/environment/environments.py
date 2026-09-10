"""Environment classification, isolation boundaries, and production safety (Task 54, Prompts #28-#30, #185, #186)."""

from __future__ import annotations

from app.environment.nodes import create_environment_node, generate_canonical_id
from app.environment.safety import ProductionSafetyViolationError
from app.environment.schemas import EnvironmentNode, EnvironmentType, NodeType, ScopeType


class EnvironmentManager:
    """Maintains logical environment boundaries and enforces production safety isolation."""

    @staticmethod
    def create_environment_node(
        env_id: str,
        env_type: EnvironmentType,
        display_name: str,
        organization_id: str,
        is_isolated: bool = True,
        source: str = "infra_manager",
    ) -> EnvironmentNode:
        canonical = generate_canonical_id(NodeType.ENVIRONMENT, env_type.value, scope_id=organization_id)
        meta = {
            "environment_type": env_type.value,
            "organization_id": organization_id,
            "is_isolated": is_isolated,
            "is_production": env_type == EnvironmentType.PRODUCTION,
        }
        return create_environment_node(
            node_id=f"env_{env_id}",
            node_type=NodeType.ENVIRONMENT,
            canonical_id=canonical,
            display_name=display_name,
            metadata=meta,
            scope=ScopeType.ENVIRONMENT,
            scope_id=organization_id,
            status="ACTIVE",
            provenance={"source": source},
            confidence=1.0,
        )

    @staticmethod
    def assert_no_cross_environment_pollution(env_a: EnvironmentType, env_b: EnvironmentType) -> None:
        """Prompt #29: Do not confuse development with production."""
        if (env_a == EnvironmentType.PRODUCTION and env_b != EnvironmentType.PRODUCTION) or \
           (env_b == EnvironmentType.PRODUCTION and env_a != EnvironmentType.PRODUCTION):
            raise ProductionSafetyViolationError(
                f"Isolation violation: Cross-boundary link detected between {env_a.value} and {env_b.value}."
            )
