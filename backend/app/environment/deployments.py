"""Deployment Model and Version Drift Check (Task 54, Prompts #138, #203)."""

from __future__ import annotations

from app.environment.nodes import create_environment_node, generate_canonical_id
from app.environment.schemas import (
    DriftSeverity,
    DriftType,
    EnvironmentDrift,
    EnvironmentNode,
    NodeType,
    ScopeType,
)
from app.environment.temporal import utc_now


class DeploymentModelManager:
    """Manages deployments and verifies desired vs actual operational versions."""

    @staticmethod
    def create_deployment_node(
        deployment_id: str,
        service_id: str,
        desired_version: str,
        actual_version: str,
        strategy: str = "rolling",
        replica_count: int = 3,
        ready_replicas: int = 3,
        rollback_target_version: str | None = None,
        environment: str = "PRODUCTION",
        source: str = "deployment_system",
    ) -> EnvironmentNode:
        canonical = generate_canonical_id(NodeType.DEPLOYMENT, f"{service_id}:{desired_version}", scope_id=environment)
        meta = {
            "service_id": service_id,
            "desired_version": desired_version,
            "actual_version": actual_version,
            "strategy": strategy,
            "replica_count": replica_count,
            "ready_replicas": ready_replicas,
            "rollback_target_version": rollback_target_version,
            "environment": environment,
            "is_converged": (desired_version == actual_version and ready_replicas == replica_count),
        }
        status = "DEPLOYED" if meta["is_converged"] else "IN_PROGRESS"
        return create_environment_node(
            node_id=f"dep_{deployment_id}",
            node_type=NodeType.DEPLOYMENT,
            canonical_id=canonical,
            display_name=f"Deploy {service_id} (v{desired_version})",
            metadata=meta,
            scope=ScopeType.ENVIRONMENT,
            scope_id=environment,
            status=status,
            provenance={"source": source},
            confidence=1.0,
        )

    @staticmethod
    def detect_deployment_drift(deployment_node: EnvironmentNode) -> EnvironmentDrift | None:
        """Prompt #138: Deployment drift must identify desired vs observed version."""
        meta = deployment_node.metadata
        desired = meta.get("desired_version")
        actual = meta.get("actual_version")
        if desired != actual:
            return EnvironmentDrift(
                drift_id=f"drf_dep_{deployment_node.node_id}",
                resource=deployment_node.node_id,
                drift_type=DriftType.DEPLOYMENT,
                expected={"version": desired},
                actual={"version": actual},
                detected_at=utc_now(),
                severity=DriftSeverity.HIGH if meta.get("environment") == "PRODUCTION" else DriftSeverity.MEDIUM,
                evidence={
                    "service_id": meta.get("service_id"),
                    "ready_replicas": meta.get("ready_replicas"),
                    "desired_replicas": meta.get("replica_count"),
                },
            )
        return None
