"""Cloud Model and Authorized Cloud Resources (Task 54, Prompts #34-#36, #88, #184)."""

from __future__ import annotations

from app.environment.nodes import create_environment_node, generate_canonical_id
from app.environment.safety import UnauthorizedDiscoveryError
from app.environment.schemas import EnvironmentNode, NodeType, ScopeType


class CloudModelManager:
    """Represents authorized multi-cloud resources with boundary enforcement."""

    @staticmethod
    def create_cloud_resource_node(
        resource_id: str,
        provider: str,  # "aws", "gcp", "azure"
        service_category: str,  # "compute", "storage", "network", "database", "queue", "serverless"
        resource_type: NodeType,
        name: str,
        region: str,
        account_or_project_id: str,
        authorized_accounts: set[str] | None = None,
        source: str = "cloud_api",
    ) -> EnvironmentNode:
        # Prompt #36, #184: Use explicit credentials and respect cloud account/project boundaries
        if authorized_accounts and account_or_project_id not in authorized_accounts:
            raise UnauthorizedDiscoveryError(
                f"Cloud account '{account_or_project_id}' is not in the list of authorized cloud boundaries."
            )

        canonical = generate_canonical_id(
            resource_type,
            f"{provider}:{region}:{name}",
            scope_id=account_or_project_id,
        )
        meta = {
            "provider": provider,
            "category": service_category,
            "region": region,
            "account_or_project_id": account_or_project_id,
            "resource_name": name,
        }
        return create_environment_node(
            node_id=f"cld_{provider}_{resource_id}",
            node_type=resource_type,
            canonical_id=canonical,
            display_name=f"[{provider.upper()}] {name} ({region})",
            metadata=meta,
            scope=ScopeType.CLOUD,
            scope_id=account_or_project_id,
            status="ACTIVE",
            provenance={"source": source, "provider": provider},
            confidence=0.98,
        )
