"""Tests for Domain Invariants and Side-Effect Validators (Task 42)."""

import pytest
from app.verification.assertions import VerificationStatus
from app.verification.invariants import InvariantEngine
from app.verification.validators import (
    CodeChangeValidator,
    DatabaseMigrationValidator,
    DeploymentValidator,
    FileWriteValidator,
)


def test_task_completed_cannot_have_active_lease_invariant():
    """Task marked COMPLETED must not retain an active execution lease (Spec 40)."""
    engine = InvariantEngine()
    violations = engine.evaluate_all({
        "task_status": "COMPLETED",
        "has_active_lease": True,
        "completion_evidence": ["ev-123"],
    })
    assert len(violations) >= 1
    assert any(v.rule_id == "TASK-001" for v in violations)


def test_task_completed_requires_completion_evidence_invariant():
    """Completed task without completion evidence violates invariant (Spec 44, 162)."""
    engine = InvariantEngine()
    violations = engine.evaluate_all({
        "task_status": "COMPLETED",
        "has_active_lease": False,
        "completion_evidence": [],
    })
    assert any(v.rule_id == "TASK-002" for v in violations)


def test_approval_invariant_expired_or_missing():
    """High-risk action cannot proceed with expired or missing approval (Spec 45)."""
    engine = InvariantEngine()
    violations = engine.evaluate_all({
        "is_high_risk": True,
        "has_approval": True,
        "approval_expired": True,
    })
    assert any(v.rule_id == "APPROVAL-001" for v in violations)


def test_deployment_validator_multi_endpoint_triangulation():
    """Deployment verification requires API status + health check + version match (Spec 23, 188, 189)."""
    # 1. Successful deployment
    pass_res = DeploymentValidator.validate_deployment(
        api_response={"status": "success", "deployed_version": "v2.0.0"},
        health_response={"status": "healthy", "version": "v2.0.0"},
        expected_version="v2.0.0",
    )
    assert pass_res.status == VerificationStatus.PASS
    assert pass_res.confidence == "HIGH"
    assert len(pass_res.discrepancies) == 0

    # 2. Tool reported success, but health check failed (Spec 158, 189)
    tool_lie_res = DeploymentValidator.validate_deployment(
        api_response={"status": "success", "deployed_version": "v2.0.0"},
        health_response={"status": "unhealthy", "code": 500},
        expected_version="v2.0.0",
    )
    assert tool_lie_res.status == VerificationStatus.FAIL
    assert any("Health endpoint reports unhealthy" in d for d in tool_lie_res.discrepancies)

    # 3. Version mismatch
    version_mismatch_res = DeploymentValidator.validate_deployment(
        api_response={"status": "success", "deployed_version": "v1.9.0"},
        health_response={"status": "healthy", "version": "v1.9.0"},
        expected_version="v2.0.0",
    )
    assert version_mismatch_res.status == VerificationStatus.FAIL
    assert any("Expected version 'v2.0.0'" in d for d in version_mismatch_res.discrepancies)


def test_code_change_validator():
    """Patch applied != code works. Verification requires tests, lint, and type check (Spec 25)."""
    # All green
    ok_res = CodeChangeValidator.validate_code_change(
        test_results={"tests_failed": 0, "tests_passed": 10},
        lint_results={"lint_errors": 0},
        type_check_results={"type_errors": 0},
    )
    assert ok_res.status == VerificationStatus.PASS

    # Tests failing
    fail_res = CodeChangeValidator.validate_code_change(
        test_results={"tests_failed": 3, "tests_passed": 7},
        lint_results={"lint_errors": 0},
        type_check_results={"type_errors": 0},
    )
    assert fail_res.status == VerificationStatus.FAIL
    assert "3 test(s) failed" in fail_res.discrepancies[0]


def test_file_write_validator():
    """File write verification checks existence and content hash (Spec 27)."""
    probe = {
        "exists": True,
        "content": "export const config = { active: true };",
    }
    pass_res = FileWriteValidator.validate_file(
        path="/app/config.js",
        expected_content="export const config = { active: true };",
        file_system_probe=probe,
    )
    assert pass_res.status == VerificationStatus.PASS

    # File missing
    missing_res = FileWriteValidator.validate_file(
        path="/app/config.js",
        expected_content="foo",
        file_system_probe={"exists": False},
    )
    assert missing_res.status == VerificationStatus.FAIL
    assert "does not exist" in missing_res.discrepancies[0]


def test_database_migration_validator():
    """Migration executed != schema correct. Verify actual database tables (Spec 26)."""
    pass_res = DatabaseMigrationValidator.validate_migration(
        migration_output={"exit_code": 0},
        schema_query_result={"tables": ["users", "orders", "verification_claims"]},
        expected_tables=["verification_claims"],
    )
    assert pass_res.status == VerificationStatus.PASS

    # Missing expected table
    fail_res = DatabaseMigrationValidator.validate_migration(
        migration_output={"exit_code": 0},
        schema_query_result={"tables": ["users", "orders"]},
        expected_tables=["verification_claims"],
    )
    assert fail_res.status == VerificationStatus.FAIL
    assert "Expected table 'verification_claims' not found" in fail_res.discrepancies[0]
