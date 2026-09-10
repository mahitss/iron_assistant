"""Environment Drift Detection and Expected vs Actual State Comparison (Task 54, Prompts #55-#58, #133-#142)."""

from __future__ import annotations

import uuid
from typing import Any

from app.environment.schemas import DriftSeverity, DriftStatus, DriftType, EnvironmentDrift
from app.environment.temporal import utc_now


class DriftDetector:
    """Detects and classifies divergences between expected (desired) and observed runtime state."""

    @staticmethod
    def create_drift_record(
        resource_id: str,
        drift_type: DriftType,
        expected: dict[str, Any],
        actual: dict[str, Any],
        evidence: dict[str, Any] | None = None,
        custom_severity: DriftSeverity | None = None,
    ) -> EnvironmentDrift:
        # Prompt #135: Security drift receives elevated priority
        if custom_severity is not None:
            severity = custom_severity
        elif drift_type == DriftType.SECURITY:
            severity = DriftSeverity.CRITICAL
        elif drift_type in (DriftType.DEPLOYMENT, DriftType.TOPOLOGY):
            severity = DriftSeverity.HIGH
        else:
            severity = DriftSeverity.MEDIUM

        did = f"drf_{uuid.uuid4().hex[:10]}"
        return EnvironmentDrift(
            drift_id=did,
            resource=resource_id,
            drift_type=drift_type,
            expected=expected,
            actual=actual,
            detected_at=utc_now(),
            severity=severity,
            evidence=evidence or {},
            status=DriftStatus.DETECTED,
        )

    @staticmethod
    def compare_expected_vs_actual(
        resource_id: str,
        expected_definition: dict[str, Any],
        actual_runtime: dict[str, Any],
        drift_type: DriftType = DriftType.CONFIGURATION,
    ) -> EnvironmentDrift | None:
        """Prompt #58: Never assume expected state is actual state. Compute concrete diff."""
        discrepancies = {}
        for key, exp_val in expected_definition.items():
            act_val = actual_runtime.get(key)
            if act_val != exp_val:
                discrepancies[key] = {"expected": exp_val, "actual": act_val}

        if discrepancies:
            return DriftDetector.create_drift_record(
                resource_id=resource_id,
                drift_type=drift_type,
                expected={k: v["expected"] for k, v in discrepancies.items()},
                actual={k: v["actual"] for k, v in discrepancies.items()},
                evidence={"diff_count": len(discrepancies), "keys": list(discrepancies.keys())},
            )
        return None
