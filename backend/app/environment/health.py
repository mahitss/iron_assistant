"""Health Model, Multi-Signal Aggregation, and Uncertainty Handling (Task 54, Prompts #93-#95, #143, #144)."""

from __future__ import annotations

from app.environment.schemas import HealthEvidence, HealthRecord, HealthStatus
from app.environment.temporal import utc_now


class HealthManager:
    """Aggregates availability, latency, error rate, saturation, and dependency health."""

    @staticmethod
    def aggregate_node_health(
        node_id: str,
        evidences: list[HealthEvidence],
        dependency_healths: list[HealthStatus] | None = None,
    ) -> HealthRecord:
        """Prompt #93, #94, #95: Aggregate signals into HealthRecord, retaining evidence."""
        # Prompt #95: Missing telemetry means UNKNOWN, not HEALTHY
        if not evidences and not dependency_healths:
            return HealthRecord(
                status=HealthStatus.UNKNOWN,
                evidence=[],
                last_checked=utc_now(),
                reason="No telemetry or dependency evidence available; state is UNKNOWN.",
            )

        has_unhealthy = False
        has_degraded = False
        reasons = []

        # Evaluate direct evidence
        for ev in evidences:
            metric = ev.metric_name.lower()
            val = ev.observed_value

            if metric in ("error_rate", "http_5xx_rate") and isinstance(val, (int, float)):
                if val >= 0.10:
                    has_unhealthy = True
                    reasons.append(f"High error rate: {val:.1%}")
                elif val >= 0.02:
                    has_degraded = True
                    reasons.append(f"Elevated error rate: {val:.1%}")
            elif metric == "status_code" and val in (500, 502, 503, 504):
                has_unhealthy = True
                reasons.append(f"Critical status code: {val}")
            elif metric in ("latency_p99", "response_time_ms") and isinstance(val, (int, float)):
                if val > 3000:
                    has_unhealthy = True
                    reasons.append(f"Extreme latency: {val}ms")
                elif val > 1000:
                    has_degraded = True
                    reasons.append(f"Elevated latency: {val}ms")
            elif metric in ("cpu_pct", "memory_pct") and isinstance(val, (int, float)):
                if val >= 95.0:
                    has_degraded = True
                    reasons.append(f"Saturation: {metric}={val}%")

        # Evaluate upstream/downstream dependency health
        if dependency_healths:
            for d_status in dependency_healths:
                if d_status == HealthStatus.UNHEALTHY:
                    has_degraded = True  # Downstream service degrades if upstream is unhealthy
                    reasons.append("Upstream dependency is UNHEALTHY")
                elif d_status == HealthStatus.DEGRADED:
                    has_degraded = True
                    reasons.append("Upstream dependency is DEGRADED")

        if has_unhealthy:
            status = HealthStatus.UNHEALTHY
        elif has_degraded:
            status = HealthStatus.DEGRADED
        elif evidences:
            status = HealthStatus.HEALTHY
        else:
            status = HealthStatus.UNKNOWN

        return HealthRecord(
            status=status,
            evidence=evidences,
            last_checked=utc_now(),
            reason="; ".join(reasons) if reasons else "Nominal operation",
        )
