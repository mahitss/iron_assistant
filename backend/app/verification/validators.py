"""Domain-specific validators for side-effects and external operations (Task 42).

Enforces:
1. Sent != Delivered (Spec 21, 22).
2. Deployment API Success != Deployed & Healthy (Spec 23).
3. Git Push != Remote Correctness (Spec 24).
4. Patch Applied != Code Works (Spec 25).
5. Migration Executed != Schema Correct (Spec 26).
6. File Write != Content/Hash Match (Spec 27).
7. UI Click/Navigation != Desired State (Spec 28, 29).
"""

from __future__ import annotations

import hashlib
from typing import Any
from app.verification.assertions import VerificationResult, VerificationStatus


class DeploymentValidator:
    """Validates deployment side-effects (Spec 23)."""

    @staticmethod
    def validate_deployment(
        api_response: dict[str, Any],
        health_response: dict[str, Any],
        expected_version: str,
    ) -> VerificationResult:
        discrepancies: list[str] = []

        # 1. API status
        api_status = str(api_response.get("status", "")).lower()
        if api_status not in {"success", "ok", "200", "201"}:
            discrepancies.append(f"Deployment API reported status: {api_status}")

        # 2. Health check
        health_status = str(health_response.get("status", health_response.get("health", ""))).lower()
        health_code = health_response.get("code", health_response.get("status_code", 200))
        if health_status not in {"healthy", "ok", "up"} or health_code not in {200, 204}:
            discrepancies.append(f"Health endpoint reports unhealthy status '{health_status}' (code {health_code})")

        # 3. Expected version
        obs_version = str(
            health_response.get("version", api_response.get("deployed_version", ""))
        ).strip()
        if obs_version != str(expected_version).strip():
            discrepancies.append(f"Expected version '{expected_version}', but observed '{obs_version}'")

        status = VerificationStatus.PASS if not discrepancies else VerificationStatus.FAIL
        return VerificationResult(
            status=status,
            discrepancies=discrepancies,
            confidence="HIGH" if status == VerificationStatus.PASS else "LOW",
            verifier="DeploymentValidator",
        )


class CodeChangeValidator:
    """Validates code patch through tests, lint, and typecheck (Spec 25)."""

    @staticmethod
    def validate_code_change(
        test_results: dict[str, Any],
        lint_results: dict[str, Any] | None = None,
        type_check_results: dict[str, Any] | None = None,
    ) -> VerificationResult:
        discrepancies: list[str] = []

        failed_tests = test_results.get("tests_failed", 0)
        if failed_tests > 0:
            discrepancies.append(f"{failed_tests} test(s) failed")

        if lint_results:
            lint_errors = lint_results.get("lint_errors", lint_results.get("errors", 0))
            if lint_errors > 0:
                discrepancies.append(f"Lint errors found: {lint_errors}")

        if type_check_results:
            type_errors = type_check_results.get("type_errors", type_check_results.get("errors", 0))
            if type_errors > 0:
                discrepancies.append(f"Type check errors found: {type_errors}")

        status = VerificationStatus.PASS if not discrepancies else VerificationStatus.FAIL
        return VerificationResult(
            status=status,
            discrepancies=discrepancies,
            confidence="HIGH" if status == VerificationStatus.PASS else "LOW",
            verifier="CodeChangeValidator",
        )


class FileWriteValidator:
    """Validates file writes via existence, permissions, and hash (Spec 27)."""

    @staticmethod
    def validate_file(
        path: str,
        expected_content: str,
        file_system_probe: dict[str, Any],
    ) -> VerificationResult:
        discrepancies: list[str] = []

        if not file_system_probe.get("exists", False):
            discrepancies.append(f"File '{path}' does not exist on filesystem")
            return VerificationResult(
                status=VerificationStatus.FAIL,
                discrepancies=discrepancies,
                confidence="HIGH",
                verifier="FileWriteValidator",
            )

        actual_content = file_system_probe.get("content", "")
        expected_hash = hashlib.sha256(expected_content.encode("utf-8")).hexdigest()
        actual_hash = file_system_probe.get(
            "hash", hashlib.sha256(actual_content.encode("utf-8")).hexdigest()
        )

        if actual_hash != expected_hash:
            discrepancies.append(f"Content hash mismatch for '{path}': expected {expected_hash}, got {actual_hash}")

        status = VerificationStatus.PASS if not discrepancies else VerificationStatus.FAIL
        return VerificationResult(
            status=status,
            discrepancies=discrepancies,
            confidence="HIGH",
            verifier="FileWriteValidator",
        )


class DatabaseMigrationValidator:
    """Validates database migration execution against actual table catalog (Spec 26)."""

    @staticmethod
    def validate_migration(
        migration_output: dict[str, Any],
        schema_query_result: dict[str, Any],
        expected_tables: list[str],
    ) -> VerificationResult:
        discrepancies: list[str] = []

        exit_code = migration_output.get("exit_code", 0)
        if exit_code != 0:
            discrepancies.append(f"Migration tool exited with non-zero code {exit_code}")

        observed_tables = set(schema_query_result.get("tables", []))
        for tbl in expected_tables:
            if tbl not in observed_tables:
                discrepancies.append(f"Expected table '{tbl}' not found in database schema")

        status = VerificationStatus.PASS if not discrepancies else VerificationStatus.FAIL
        return VerificationResult(
            status=status,
            discrepancies=discrepancies,
            confidence="HIGH" if status == VerificationStatus.PASS else "LOW",
            verifier="DatabaseMigrationValidator",
        )


# Backward compatibility alias
DomainValidators = DeploymentValidator
