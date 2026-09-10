"""Service Model and Evidence-based Service Health (Task 54, Prompts #20-#22, #87)."""

from __future__ import annotations

from app.environment.nodes import create_environment_node, generate_canonical_id
from app.environment.schemas import (
    EnvironmentNode,
    HealthEvidence,
    HealthRecord,
    HealthStatus,
    NodeType,
    ScopeType,
)
from app.environment.temporal import utc_now


class ServiceModelManager:
    """Manages service definitions and evidence-backed health evaluation."""

    @staticmethod
    def create_service_node(
        service_id: str,
        name: str,
        version: str,
        instances: int = 1,
        endpoints: list[str] | None = None,
        environment: str = "PRODUCTION",
        scope_id: str | None = None,
        source: str = "service_mesh",
    ) -> EnvironmentNode:
        canonical = generate_canonical_id(NodeType.SERVICE, f"{name}:{version}", scope_id=environment)
        meta = {
            "service_name": name,
            "version": version,
            "instances": instances,
            "endpoints": endpoints or [],
            "environment": environment,
        }
        return create_environment_node(
            node_id=f"svc_{service_id}",
            node_type=NodeType.SERVICE,
            canonical_id=canonical,
            display_name=f"{name} ({environment})",
            metadata=meta,
            scope=ScopeType.APPLICATION,
            scope_id=scope_id or service_id,
            status=HealthStatus.UNKNOWN.value,  # Prompt #95: missing telemetry means UNKNOWN, not HEALTHY
            provenance={"source": source, "collector": "service_discovery"},
            confidence=0.95,
        )

    @staticmethod
    def evaluate_service_health(
        service_id: str,
        evidence: list[HealthEvidence],
    ) -> HealthRecord:
        """Prompt #22: Health must reference evidence. Prompt #95: Missing evidence means UNKNOWN."""
        if not evidence:
            return HealthRecord(
                status=HealthStatus.UNKNOWN,
                evidence=[],
                last_checked=utc_now(),
                reason="No telemetry or health evidence provided; defaulting to UNKNOWN.",
            )

        # Check for error rates or down signals in evidence
        has_critical = False
        has_degraded = False

        for ev in evidence:
            val = ev.observed_value
            # Error rate threshold check
            if ev.metric_name in ("error_rate", "http_5xx_rate") and isinstance(val, (int, float)):
                if val >= 0.15:  # > 15% error rate is unhealthy
                    has_critical = True
                elif val >= 0.05:
                    has_degraded = True
            elif ev.metric_name == "status_code" and val in (500, 502, 503, 504):
                has_critical = True
            elif ev.metric_name == "latency_p99" and isinstance(val, (int, float)) and val > 2000:
                has_degraded = True

        if has_critical:
            status = HealthStatus.UNHEALTHY
            reason = "Critical telemetry thresholds breached in provided evidence."
        elif has_degraded:
            status = HealthStatus.DEGRADED
            reason = "Telemetry indicates latency or moderate error degradation."
        else:
            status = HealthStatus.HEALTHY
            reason = "All evidence within nominal thresholds."

        return HealthRecord(
            status=status,
            evidence=evidence,
            last_checked=utc_now(),
            reason=reason,
        )
