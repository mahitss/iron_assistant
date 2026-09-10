"""Unit and integration tests for execution boundary firewall, secret scrubbing, audit chain, and service facade (Task 59)."""

import pytest

from app.orchestration.audit import OrchestrationAuditor
from app.orchestration.plans import OrchestrationLifecycleManager
from app.orchestration.privacy import OrchestrationPrivacyManager
from app.orchestration.safety import (
    OrchestrationExecutionBoundaryError,
    StaleOrchestrationError,
    block_direct_tool_execution,
    scrub_orchestration_secrets,
)
from app.orchestration.schemas import (
    OrchestrationPlan,
    ProviderAssignment,
)
from app.orchestration.service import OrchestrationService


def test_execution_boundary_firewall_blocks_direct_tool_execution():
    """Test Invariant 3 & 108: Orchestrator coordinates; it NEVER directly executes production tools.

    Tool execution must flow via ToolExecutor with Policy, Authorization, and Approval gates.
    """
    with pytest.raises(OrchestrationExecutionBoundaryError, match="Execution Boundary Violation"):
        block_direct_tool_execution("deploy_container_tool", {"image": "kairo:v2"})

    with pytest.raises(OrchestrationExecutionBoundaryError, match="Execution Boundary Violation"):
        block_direct_tool_execution("bash_command", {"cmd": "rm -rf /"})


def test_secret_and_credential_scrubbing():
    """Test Invariant 17 & 69: API keys, tokens, passwords, and private keys are scrubbed."""
    raw_text = "Deploying using api_key='AKIAIOSFODNN7EXAMPLE' and Bearer token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    scrubbed = scrub_orchestration_secrets(raw_text)
    assert "AKIAIOSFODNN7EXAMPLE" not in scrubbed
    assert "[REDACTED_SECRET]" in scrubbed

    priv_key = "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA0\n-----END RSA PRIVATE KEY-----"
    scrubbed_key = scrub_orchestration_secrets(priv_key)
    assert "MIIEowIBAAKCAQEA0" not in scrubbed_key


def test_privacy_manager_context_sanitization_and_pii():
    """Verify privacy manager sanitizes context, removes internal keys, and masks PII."""
    mgr = OrchestrationPrivacyManager()
    ctx = {
        "__internal_token": "secret123",
        "password": "supersecretpassword",
        "contact_email": "admin@example.com",
        "server_ip": "192.168.1.100",
        "environment": "production",
    }
    sanitized = mgr.sanitize_context(ctx)
    assert sanitized["password"] == "[REDACTED]"
    assert sanitized["contact_email"] == "[EMAIL_REDACTED]"
    assert sanitized["server_ip"] == "[IP_REDACTED]"
    assert sanitized["environment"] == "production"


def test_stale_orchestration_detection_and_revalidation():
    """Test Invariants 14 & 76: Environmental drift or permission revocation requires revalidation."""
    mgr = OrchestrationLifecycleManager()

    plan = OrchestrationPlan(
        name="Production Upgrade",
        assignments=[
            ProviderAssignment(
                task_id="task_upgrade",
                provider_name="DeployAgent",
                capability_id="cap_deploy",
                required_permissions=["deploy.production"],
            )
        ],
    )
    mgr.save_plan(plan)

    # 1. Healthy revalidation passes
    assert mgr.revalidate_plan(
        orchestration_id=plan.orchestration_id,
        current_environment="production",
        active_permissions={"deploy.production"},
    ) is True

    # 2. Permission revoked triggers StaleOrchestrationError
    with pytest.raises(StaleOrchestrationError, match="requires revalidation"):
        mgr.revalidate_plan(
            orchestration_id=plan.orchestration_id,
            current_environment="production",
            active_permissions=set(),  # revoked!
        )

    # 3. Provider becomes unhealthy triggers StaleOrchestrationError
    with pytest.raises(StaleOrchestrationError, match="requires revalidation"):
        mgr.revalidate_plan(
            orchestration_id=plan.orchestration_id,
            current_environment="production",
            active_permissions={"deploy.production"},
            unhealthy_providers={"DeployAgent"},
        )


def test_tamper_evident_audit_trail_integrity():
    """Verify cryptographic audit trail with SHA-256 hash chains."""
    auditor = OrchestrationAuditor()

    e1 = auditor.record_event("ORCHESTRATION_CREATED", "SystemUser", {"plan": "Plan 1"})
    e2 = auditor.record_event("RESOURCE_RESERVED", "SystemUser", {"res": "Compute 1"})
    e3 = auditor.record_event("TASK_ASSIGNED", "SystemUser", {"task": "Task 1"})

    assert e1["previous_hash"] == "0" * 64
    assert e2["previous_hash"] == e1["hash"]
    assert e3["previous_hash"] == e2["hash"]
    assert auditor.verify_integrity() is True

    # Tampering with an audit entry causes verification failure
    auditor._audit_log[1]["details"]["res"] = "Tampered Compute"
    assert auditor.verify_integrity() is False


@pytest.mark.asyncio
async def test_orchestration_service_flow():
    """Verify full end-to-end service orchestration workflow."""
    service = OrchestrationService()

    tasks = [
        {
            "id": "t_calc",
            "title": "Calculate metrics",
            "required_capabilities": ["calculate"],
            "environment": "development",
        },
        {
            "id": "t_sys",
            "title": "Check system info",
            "required_capabilities": ["system_info"],
            "environment": "development",
        },
    ]

    # Analyze
    analysis = await service.analyze(tasks, environment="development")
    assert analysis["feasibility"] in ("FEASIBLE", "PARTIALLY_FEASIBLE")
    assert analysis["total_tasks"] == 2

    # Create plan
    plan = await service.create_orchestration_plan(
        name="Automated System Audit",
        tasks=tasks,
        dependencies={"t_sys": ["t_calc"]},
        environment="development",
    )

    assert plan.name == "Automated System Audit"
    assert len(plan.assignments) == 2
    assert len(plan.execution_waves) == 2

    # Explanation
    explanation = service.explain_task("t_calc")
    assert explanation["found"] is True
    assert "t_calc" in explanation["explanation"]
