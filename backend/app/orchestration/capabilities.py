"""Capability definitions, metadata schemas, and environment validators for Orchestration (Task 59)."""

from __future__ import annotations

import logging
from typing import Any

from app.orchestration.safety import OrchestrationSafetyError, sanitize_orchestration_directive
from app.orchestration.schemas import (
    CapabilityDefinition,
    CapabilityStatus,
    RiskSeverity,
)

logger = logging.getLogger(__name__)

# Standard trusted capability IDs
STANDARD_CAPABILITIES = {
    "read_repository": "Inspect and query code repositories and files",
    "inspect_logs": "Read, query, and filter application and system logs",
    "deploy_service": "Deploy containerized services or serverless functions",
    "modify_configuration": "Update configuration files or environment parameters",
    "run_tests": "Execute unit, integration, and end-to-end test suites",
    "execute_sql": "Run verified SQL queries against authorized databases",
    "analyze_data": "Perform data analysis, aggregation, and anomaly detection",
    "generate_code": "Synthesize or refactor code modules and documentation",
    "verify_deployment": "Verify service health, smoke tests, and HTTP status codes",
    "query_cloud_state": "Query cloud infrastructure resources and cluster topology",
    "create_backup": "Create snapshot backups of persistent storage or databases",
    "rollback_deployment": "Safely revert deployment to a previous healthy version",
    "web_search": "Execute safe web search queries for real-time information",
    "web_fetch": "Fetch and extract text content from public URLs",
    "calculate": "Perform deterministic mathematical and arithmetic computations",
    "system_info": "Inspect local OS, environment, and runtime metrics",
}

# Privileged capabilities requiring strict verification and elevated privileges
PRIVILEGED_CAPABILITIES = {
    "deploy_service",
    "rollback_deployment",
    "modify_configuration",
    "execute_sql",
    "create_backup",
}


def create_capability(
    name: str,
    provider: str,
    description: str = "",
    capability_id: str | None = None,
    version: str = "1.0.0",
    reliability: float = 1.0,
    latency_ms: float = 50.0,
    cost_estimate: float = 0.0,
    risk_level: RiskSeverity = RiskSeverity.LOW,
    supported_environments: list[str] | None = None,
    required_permissions: list[str] | None = None,
    required_resources: list[dict[str, Any]] | None = None,
    input_schema: dict[str, Any] | None = None,
    output_schema: dict[str, Any] | None = None,
    verification_method: str = "ASSERTION",
    status: CapabilityStatus = CapabilityStatus.AVAILABLE,
    provenance: dict[str, Any] | None = None,
    is_trusted_registration: bool = True,
) -> CapabilityDefinition:
    """Safely build and validate a CapabilityDefinition."""
    # Sanitize strings to avoid prompt injections
    clean_name = sanitize_orchestration_directive(name)
    clean_description = sanitize_orchestration_directive(description or STANDARD_CAPABILITIES.get(clean_name, ""))

    # Check if untrusted registration is trying to claim a privileged capability
    if clean_name in PRIVILEGED_CAPABILITIES and not is_trusted_registration:
        raise OrchestrationSafetyError(
            f"Privilege Escalation Blocked: Untrusted source cannot register privileged capability '{clean_name}'."
        )

    cid = capability_id or f"cap_{clean_name}_{provider.lower()}"
    envs = supported_environments or ["development", "staging", "production"]
    perms = required_permissions or []

    # Assign elevated risk if privileged
    calculated_risk = risk_level
    if clean_name in PRIVILEGED_CAPABILITIES and calculated_risk == RiskSeverity.LOW:
        calculated_risk = RiskSeverity.HIGH

    return CapabilityDefinition(
        capability_id=cid,
        name=clean_name,
        description=clean_description,
        version=version,
        provider=provider,
        reliability=max(0.0, min(1.0, reliability)),
        latency_ms=max(0.0, latency_ms),
        cost_estimate=max(0.0, cost_estimate),
        risk_level=calculated_risk,
        supported_environments=[e.lower() for e in envs],
        required_permissions=perms,
        required_resources=required_resources or [],
        input_schema=input_schema or {},
        output_schema=output_schema or {},
        verification_method=verification_method,
        status=status,
        provenance=provenance or {"registered_by": "system", "is_trusted": is_trusted_registration},
    )
