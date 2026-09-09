"""Verification Strategy Registry & Dispatcher for Kairo (Task 42).

Implements the 10 core verification strategies (Spec 47), ensuring that
verification actions are strictly read-only by default, preventing unintended
side-effects or premature success assertions.
"""

from __future__ import annotations

import enum
import hashlib
import logging
import time
from typing import Any, Callable

from app.verification.assertions import VerificationContract, VerificationResult, VerificationStatus
from app.verification.evidence import Evidence, EvidenceType

logger = logging.getLogger("kairo.verification.strategies")


class VerificationStrategyType(str, enum.Enum):
    """The 10 supported verification strategies (Spec 47)."""

    DIRECT_CHECK = "DIRECT_CHECK"
    STATE_QUERY = "STATE_QUERY"
    HEALTH_CHECK = "HEALTH_CHECK"
    TEST_EXECUTION = "TEST_EXECUTION"
    HASH_COMPARISON = "HASH_COMPARISON"
    DIFF_COMPARISON = "DIFF_COMPARISON"
    SOURCE_COMPARISON = "SOURCE_COMPARISON"
    INVARIANT_CHECK = "INVARIANT_CHECK"
    RECONCILIATION = "RECONCILIATION"
    USER_CONFIRMATION = "USER_CONFIRMATION"


class VerificationStrategyExecutor:
    """Executes verification strategies according to contract definitions."""

    def __init__(self) -> None:
        self._handlers: dict[str, Callable[..., VerificationResult]] = {
            VerificationStrategyType.DIRECT_CHECK.value: self._verify_direct_check,
            VerificationStrategyType.STATE_QUERY.value: self._verify_state_query,
            VerificationStrategyType.HEALTH_CHECK.value: self._verify_health_check,
            VerificationStrategyType.TEST_EXECUTION.value: self._verify_test_execution,
            VerificationStrategyType.HASH_COMPARISON.value: self._verify_hash_comparison,
            VerificationStrategyType.DIFF_COMPARISON.value: self._verify_diff_comparison,
            VerificationStrategyType.SOURCE_COMPARISON.value: self._verify_source_comparison,
            VerificationStrategyType.INVARIANT_CHECK.value: self._verify_invariant_check,
            VerificationStrategyType.RECONCILIATION.value: self._verify_reconciliation,
            VerificationStrategyType.USER_CONFIRMATION.value: self._verify_user_confirmation,
        }

    def execute(
        self,
        strategy_name: str,
        contract: VerificationContract,
        observed_data: dict[str, Any],
    ) -> VerificationResult:
        """Dispatch strategy execution with duration and error tracking."""
        start_time = time.monotonic()
        handler = self._handlers.get(strategy_name.upper())

        if not handler:
            duration_ms = (time.monotonic() - start_time) * 1000.0
            return VerificationResult(
                status=VerificationStatus.INCONCLUSIVE,
                discrepancies=[f"Unsupported verification strategy: '{strategy_name}'"],
                confidence="LOW",
                verifier=strategy_name,
                duration_ms=duration_ms,
            )

        try:
            result = handler(contract, observed_data)
            result.duration_ms = (time.monotonic() - start_time) * 1000.0
            return result
        except TimeoutError:
            duration_ms = (time.monotonic() - start_time) * 1000.0
            return VerificationResult(
                status=VerificationStatus.TIMEOUT,
                discrepancies=[f"Verification timed out after contract limit ({contract.timeout_seconds}s)"],
                confidence="LOW",
                verifier=strategy_name,
                duration_ms=duration_ms,
            )
        except Exception as exc:
            logger.exception("Error executing verification strategy '%s': %s", strategy_name, exc)
            duration_ms = (time.monotonic() - start_time) * 1000.0
            return VerificationResult(
                status=VerificationStatus.FAIL,
                discrepancies=[f"Strategy execution error: {str(exc)}"],
                confidence="LOW",
                verifier=strategy_name,
                duration_ms=duration_ms,
            )

    # 1. DIRECT_CHECK
    def _verify_direct_check(self, contract: VerificationContract, data: dict[str, Any]) -> VerificationResult:
        target = contract.target
        expected = contract.expected_state
        discrepancies = []

        for k, v in expected.items():
            actual = data.get(k)
            if actual != v:
                discrepancies.append(f"Field '{k}': expected '{v}', observed '{actual}'")

        status = VerificationStatus.PASS if not discrepancies else VerificationStatus.FAIL
        return VerificationResult(
            status=status,
            discrepancies=discrepancies,
            confidence="HIGH" if status == VerificationStatus.PASS else "MEDIUM",
            verifier="DIRECT_CHECK",
        )

    # 2. STATE_QUERY
    def _verify_state_query(self, contract: VerificationContract, data: dict[str, Any]) -> VerificationResult:
        query_state = data.get("query_result", {})
        expected = contract.expected_state
        discrepancies = []

        for k, v in expected.items():
            if query_state.get(k) != v:
                discrepancies.append(f"Query match fail on '{k}': expected {v}, got {query_state.get(k)}")

        status = VerificationStatus.PASS if not discrepancies else VerificationStatus.FAIL
        return VerificationResult(
            status=status,
            discrepancies=discrepancies,
            confidence="HIGH" if status == VerificationStatus.PASS else "LOW",
            verifier="STATE_QUERY",
        )

    # 3. HEALTH_CHECK
    def _verify_health_check(self, contract: VerificationContract, data: dict[str, Any]) -> VerificationResult:
        health_status = str(data.get("health", data.get("status", ""))).lower()
        http_code = data.get("status_code", 200)

        discrepancies = []
        if health_status not in ["healthy", "ok", "up", "alive"]:
            discrepancies.append(f"Health check status is '{health_status}', expected 'healthy'")
        if http_code not in [200, 204]:
            discrepancies.append(f"Health endpoint returned HTTP {http_code}")

        status = VerificationStatus.PASS if not discrepancies else VerificationStatus.FAIL
        return VerificationResult(
            status=status,
            discrepancies=discrepancies,
            confidence="HIGH" if status == VerificationStatus.PASS else "MEDIUM",
            verifier="HEALTH_CHECK",
        )

    # 4. TEST_EXECUTION
    def _verify_test_execution(self, contract: VerificationContract, data: dict[str, Any]) -> VerificationResult:
        tests_passed = data.get("tests_passed", 0)
        tests_failed = data.get("tests_failed", 0)
        exit_code = data.get("exit_code", 0)

        discrepancies = []
        if tests_failed > 0:
            discrepancies.append(f"{tests_failed} test(s) failed")
        if exit_code != 0:
            discrepancies.append(f"Test runner exited with code {exit_code}")
        if tests_passed == 0 and tests_failed == 0:
            discrepancies.append("No tests were executed (empty test suite)")

        status = VerificationStatus.PASS if not discrepancies else VerificationStatus.FAIL
        return VerificationResult(
            status=status,
            discrepancies=discrepancies,
            confidence="HIGH" if status == VerificationStatus.PASS else "LOW",
            verifier="TEST_EXECUTION",
        )

    # 5. HASH_COMPARISON
    def _verify_hash_comparison(self, contract: VerificationContract, data: dict[str, Any]) -> VerificationResult:
        expected_hash = str(contract.expected_state.get("hash", "")).lower()
        content = data.get("content")
        actual_hash = str(data.get("hash", "")).lower()

        if not actual_hash and content is not None:
            actual_hash = hashlib.sha256(content.encode("utf-8") if isinstance(content, str) else content).hexdigest()

        discrepancies = []
        if not actual_hash or actual_hash != expected_hash:
            discrepancies.append(f"Hash mismatch: expected {expected_hash}, got {actual_hash}")

        status = VerificationStatus.PASS if not discrepancies else VerificationStatus.FAIL
        return VerificationResult(
            status=status,
            discrepancies=discrepancies,
            confidence="HIGH",
            verifier="HASH_COMPARISON",
        )

    # 6. DIFF_COMPARISON
    def _verify_diff_comparison(self, contract: VerificationContract, data: dict[str, Any]) -> VerificationResult:
        expected_files = set(contract.expected_state.get("changed_files", []))
        actual_files = set(data.get("changed_files", []))

        discrepancies = []
        missing = expected_files - actual_files
        unexpected = actual_files - expected_files
        if missing:
            discrepancies.append(f"Missing expected diff changes for: {list(missing)}")
        if unexpected and contract.expected_state.get("strict_files", False):
            discrepancies.append(f"Unexpected file changes detected: {list(unexpected)}")

        status = VerificationStatus.PASS if not discrepancies else VerificationStatus.FAIL
        return VerificationResult(
            status=status,
            discrepancies=discrepancies,
            confidence="HIGH" if status == VerificationStatus.PASS else "MEDIUM",
            verifier="DIFF_COMPARISON",
        )

    # 7. SOURCE_COMPARISON
    def _verify_source_comparison(self, contract: VerificationContract, data: dict[str, Any]) -> VerificationResult:
        source_text = str(data.get("source_text", "")).lower()
        expected_substrings = contract.expected_state.get("contains", [])

        discrepancies = []
        for s in expected_substrings:
            if str(s).lower() not in source_text:
                discrepancies.append(f"Required excerpt '{s}' missing from source")

        status = VerificationStatus.PASS if not discrepancies else VerificationStatus.FAIL
        return VerificationResult(
            status=status,
            discrepancies=discrepancies,
            confidence="MEDIUM",
            verifier="SOURCE_COMPARISON",
        )

    # 8. INVARIANT_CHECK
    def _verify_invariant_check(self, contract: VerificationContract, data: dict[str, Any]) -> VerificationResult:
        violations = data.get("invariant_violations", [])
        discrepancies = [f"Invariant violated: {v}" for v in violations]
        status = VerificationStatus.PASS if not discrepancies else VerificationStatus.FAIL
        return VerificationResult(
            status=status,
            discrepancies=discrepancies,
            confidence="HIGH",
            verifier="INVARIANT_CHECK",
        )

    # 9. RECONCILIATION
    def _verify_reconciliation(self, contract: VerificationContract, data: dict[str, Any]) -> VerificationResult:
        in_sync = data.get("in_sync", False)
        discrepancies = data.get("drift_items", [])
        status = VerificationStatus.PASS if (in_sync and not discrepancies) else VerificationStatus.FAIL
        return VerificationResult(
            status=status,
            discrepancies=discrepancies,
            confidence="HIGH" if status == VerificationStatus.PASS else "LOW",
            verifier="RECONCILIATION",
        )

    # 10. USER_CONFIRMATION (Spec 48: Evidence, but not replacement for system verification)
    def _verify_user_confirmation(self, contract: VerificationContract, data: dict[str, Any]) -> VerificationResult:
        confirmed = data.get("confirmed", False)
        requires_system = contract.expected_state.get("requires_system_verification", False)

        discrepancies = []
        if not confirmed:
            discrepancies.append("User declined confirmation or confirmation was not provided")
        elif requires_system:
            discrepancies.append("User confirmed, but mandatory system-level verification is required and pending")

        if not confirmed:
            status = VerificationStatus.FAIL
        elif requires_system:
            status = VerificationStatus.PARTIAL
        else:
            status = VerificationStatus.PASS

        return VerificationResult(
            status=status,
            discrepancies=discrepancies,
            confidence="MEDIUM" if status == VerificationStatus.PASS else "LOW",
            verifier="USER_CONFIRMATION",
        )
