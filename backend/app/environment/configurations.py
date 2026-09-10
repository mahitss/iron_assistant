"""Configuration Model, Version Tracking, and Secret Redaction (Task 54, Prompts #51-#54, #136, #187, #190)."""

from __future__ import annotations

from typing import Any

from app.environment.nodes import create_environment_node, generate_canonical_id
from app.environment.safety import EnvironmentSafetyGuard
from app.environment.schemas import (
    DriftSeverity,
    DriftType,
    EnvironmentDrift,
    EnvironmentNode,
    NodeType,
    ScopeType,
)
from app.environment.temporal import utc_now


class ConfigurationManager:
    """Manages configuration parameters, versions, and drift detection without storing secrets."""

    @staticmethod
    def create_configuration_node(
        config_id: str,
        name: str,
        parameters: dict[str, Any],
        version: int = 1,
        scope_id: str | None = None,
        source: str = "config_provider",
    ) -> EnvironmentNode:
        # Prompt #52, #187: Never store secret values in the Digital Twin. Redact sensitive configuration.
        sanitized_params = EnvironmentSafetyGuard.inspect_and_sanitize_metadata(parameters, raise_on_secret=True)
        canonical = generate_canonical_id(NodeType.CONFIGURATION, name, scope_id=scope_id)
        meta = {
            "config_name": name,
            "version": version,
            "parameters": sanitized_params,
        }
        return create_environment_node(
            node_id=f"cfg_{config_id}",
            node_type=NodeType.CONFIGURATION,
            canonical_id=canonical,
            display_name=f"{name} (v{version})",
            metadata=meta,
            scope=ScopeType.SYSTEM,
            scope_id=scope_id,
            status="ACTIVE",
            provenance={"source": source},
            confidence=1.0,
        )

    @staticmethod
    def detect_configuration_drift(
        config_node: EnvironmentNode,
        expected_params: dict[str, Any],
    ) -> EnvironmentDrift | None:
        """Prompt #54, #136: Compare expected and observed configuration."""
        actual_params = config_node.metadata.get("parameters", {})
        diffs = {}
        for k, exp_v in expected_params.items():
            act_v = actual_params.get(k)
            if act_v != exp_v:
                diffs[k] = {"expected": exp_v, "actual": act_v}

        if diffs:
            return EnvironmentDrift(
                drift_id=f"drf_cfg_{config_node.node_id}",
                resource=config_node.node_id,
                drift_type=DriftType.CONFIGURATION,
                expected={"drifted_keys": list(diffs.keys()), "expected_values": {k: v["expected"] for k, v in diffs.items()}},
                actual={"drifted_keys": list(diffs.keys()), "actual_values": {k: v["actual"] for k, v in diffs.items()}},
                detected_at=utc_now(),
                severity=DriftSeverity.HIGH if any("auth" in k.lower() or "sec" in k.lower() for k in diffs) else DriftSeverity.MEDIUM,
                evidence={"diffs": diffs, "version": config_node.metadata.get("version")},
            )
        return None
