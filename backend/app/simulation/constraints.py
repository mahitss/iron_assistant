"""Resource constraint verification and capacity checking for hypothetical scenarios."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ConstraintCheckResult(BaseModel):
    """Result of checking a scenario or hypothetical state against resource constraints."""

    is_valid: bool = True
    status: str = "WITHIN_LIMITS"  # WITHIN_LIMITS, AT_RISK, VIOLATED
    violations: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    metrics_checked: dict[str, Any] = Field(default_factory=dict)


class ConstraintValidator:
    """Validates CPU, memory, replica, connection, and storage constraints."""

    DEFAULT_LIMITS = {
        "max_replicas_per_service": 50,
        "max_cpu_cores": 128.0,
        "max_memory_gb": 512.0,
        "max_queue_depth": 10000,
        "max_latency_ms": 2000.0,
    }

    def validate_constraints(
        self,
        hypothetical_state: dict[str, Any],
        scenario_constraints: list[dict[str, Any]] | None = None,
    ) -> ConstraintCheckResult:
        """Evaluates hypothetical state against system limits and custom scenario constraints."""
        violations: list[str] = []
        warnings: list[str] = []
        checked: dict[str, Any] = {}

        # 1. Check services replica constraints
        services = hypothetical_state.get("services", {})
        for svc_name, svc_info in services.items():
            if isinstance(svc_info, dict):
                replicas = svc_info.get("replicas", 1)
                checked[f"{svc_name}.replicas"] = replicas
                if replicas > self.DEFAULT_LIMITS["max_replicas_per_service"]:
                    violations.append(
                        f"Service '{svc_name}' requested {replicas} replicas, exceeding maximum cluster limit of {self.DEFAULT_LIMITS['max_replicas_per_service']}."
                    )
                elif replicas > (self.DEFAULT_LIMITS["max_replicas_per_service"] * 0.8):
                    warnings.append(
                        f"Service '{svc_name}' replica count ({replicas}) approaching cluster ceiling."
                    )

        # 2. Check network latency limits
        latencies = hypothetical_state.get("network_latency", {})
        for node, lat in latencies.items():
            checked[f"latency.{node}"] = lat
            if lat > self.DEFAULT_LIMITS["max_latency_ms"]:
                violations.append(
                    f"Node '{node}' simulated latency of {lat}ms exceeds SLA limit of {self.DEFAULT_LIMITS['max_latency_ms']}ms."
                )

        # 3. Check custom scenario constraints
        if scenario_constraints:
            for constraint in scenario_constraints:
                metric = constraint.get("metric")
                max_val = constraint.get("max_value")
                min_val = constraint.get("min_value")
                curr_val = hypothetical_state.get(metric)
                if curr_val is not None:
                    checked[metric] = curr_val
                    if max_val is not None and curr_val > max_val:
                        violations.append(
                            f"Custom constraint violated: {metric}={curr_val} exceeds max limit {max_val}."
                        )
                    if min_val is not None and curr_val < min_val:
                        violations.append(
                            f"Custom constraint violated: {metric}={curr_val} below min limit {min_val}."
                        )

        if violations:
            status = "VIOLATED"
            is_valid = False
        elif warnings:
            status = "AT_RISK"
            is_valid = True
        else:
            status = "WITHIN_LIMITS"
            is_valid = True

        return ConstraintCheckResult(
            is_valid=is_valid,
            status=status,
            violations=violations,
            warnings=warnings,
            metrics_checked=checked,
        )
