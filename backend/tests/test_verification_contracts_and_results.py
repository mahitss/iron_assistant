"""Tests for Verification Contracts, Results, and 10 Strategies (Task 42)."""

import hashlib
import pytest
from app.verification.assertions import (
    VerificationContract,
    VerificationResult,
    VerificationStatus,
)
from app.verification.strategies import (
    VerificationStrategyExecutor,
    VerificationStrategyType,
)


def test_verification_contract_creation():
    """Verify contract fields and defaults."""
    contract = VerificationContract(
        target="service_api",
        expected_state={"status": "running", "port": 8000},
        timeout_seconds=15.0,
    )
    assert contract.target == "service_api"
    assert contract.expected_state["status"] == "running"
    assert contract.timeout_seconds == 15.0


def test_strategy_direct_check():
    """DIRECT_CHECK compares observed data against expected state."""
    executor = VerificationStrategyExecutor()
    contract = VerificationContract(
        target="config",
        expected_state={"debug": False, "env": "production"},
    )

    # Passing case
    pass_res = executor.execute(
        VerificationStrategyType.DIRECT_CHECK.value,
        contract,
        {"debug": False, "env": "production"},
    )
    assert pass_res.status == VerificationStatus.PASS
    assert pass_res.confidence == "HIGH"
    assert len(pass_res.discrepancies) == 0

    # Failing case
    fail_res = executor.execute(
        VerificationStrategyType.DIRECT_CHECK.value,
        contract,
        {"debug": True, "env": "production"},
    )
    assert fail_res.status == VerificationStatus.FAIL
    assert "debug" in fail_res.discrepancies[0]


def test_strategy_health_check():
    """HEALTH_CHECK verifies health status and status code."""
    executor = VerificationStrategyExecutor()
    contract = VerificationContract(target="api", expected_state={})

    ok_res = executor.execute(
        VerificationStrategyType.HEALTH_CHECK.value,
        contract,
        {"health": "healthy", "status_code": 200},
    )
    assert ok_res.status == VerificationStatus.PASS

    down_res = executor.execute(
        VerificationStrategyType.HEALTH_CHECK.value,
        contract,
        {"health": "degraded", "status_code": 503},
    )
    assert down_res.status == VerificationStatus.FAIL
    assert len(down_res.discrepancies) == 2


def test_strategy_test_execution():
    """TEST_EXECUTION checks for passing tests and detects empty test runs (Spec 128, 147)."""
    executor = VerificationStrategyExecutor()
    contract = VerificationContract(target="ci_suite", expected_state={})

    # Pass
    pass_res = executor.execute(
        VerificationStrategyType.TEST_EXECUTION.value,
        contract,
        {"tests_passed": 42, "tests_failed": 0, "exit_code": 0},
    )
    assert pass_res.status == VerificationStatus.PASS

    # Fail
    fail_res = executor.execute(
        VerificationStrategyType.TEST_EXECUTION.value,
        contract,
        {"tests_passed": 40, "tests_failed": 2, "exit_code": 1},
    )
    assert fail_res.status == VerificationStatus.FAIL
    assert "2 test(s) failed" in fail_res.discrepancies[0]

    # Empty tests run
    empty_res = executor.execute(
        VerificationStrategyType.TEST_EXECUTION.value,
        contract,
        {"tests_passed": 0, "tests_failed": 0, "exit_code": 0},
    )
    assert empty_res.status == VerificationStatus.FAIL
    assert "empty test suite" in empty_res.discrepancies[0]


def test_strategy_hash_comparison():
    """HASH_COMPARISON computes and compares SHA256 hashes of artifacts (Spec 130)."""
    executor = VerificationStrategyExecutor()
    content = "release artifact build v2.1.0"
    expected_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

    contract = VerificationContract(
        target="artifact.tar.gz",
        expected_state={"hash": expected_hash},
    )

    pass_res = executor.execute(
        VerificationStrategyType.HASH_COMPARISON.value,
        contract,
        {"content": content},
    )
    assert pass_res.status == VerificationStatus.PASS

    corrupted_res = executor.execute(
        VerificationStrategyType.HASH_COMPARISON.value,
        contract,
        {"content": "tampered content"},
    )
    assert corrupted_res.status == VerificationStatus.FAIL
    assert "Hash mismatch" in corrupted_res.discrepancies[0]


def test_strategy_user_confirmation_partial():
    """User confirmation alone is PARTIAL if system verification is mandatory (Spec 48)."""
    executor = VerificationStrategyExecutor()
    contract = VerificationContract(
        target="critical_action",
        expected_state={"requires_system_verification": True},
    )

    result = executor.execute(
        VerificationStrategyType.USER_CONFIRMATION.value,
        contract,
        {"confirmed": True},
    )
    # User confirmed, but system verification is required -> PARTIAL
    assert result.status == VerificationStatus.PARTIAL
    assert "mandatory system-level verification is required" in result.discrepancies[0]
