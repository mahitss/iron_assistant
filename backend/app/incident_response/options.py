"""Response option generation, capability verification, and reversibility evaluation (Task 61)."""

from __future__ import annotations

import logging
import uuid

from app.incident_response.schemas import (
    IncidentSeverity,
    ResponseOptionItem,
)

logger = logging.getLogger(__name__)

# Standard Kairo operational capabilities from Task 59 catalog
_STANDARD_CAPABILITIES = {
    "scale": "compute.scale",
    "contain": "traffic.rate_limit",
    "rollback": "deployment.rollback",
    "failover": "routing.failover",
    "restart": "compute.restart",
    "isolate": "network.isolate",
}


class ResponseOptionEngine:
    """Generates valid candidate response strategies, validates capability availability, and evaluates reversibility.

    Invariant 25-27: Options are evaluated for risk, reversibility, and benefit; no fabricated actions allowed.
    Invariant 36: Reversible mitigations are prioritized when risks are comparable.
    """

    def generate_options(
        self,
        incident_id: str,
        severity: IncidentSeverity,
        affected_resources: list[str],
        leading_cause: str | None = None,
        available_capabilities: list[str] | None = None,
    ) -> list[ResponseOptionItem]:
        """Generate candidate response options evaluating feasibility, risk, and capability requirements."""
        caps = set(
            available_capabilities
            or [
                "compute.scale",
                "traffic.rate_limit",
                "deployment.rollback",
                "routing.failover",
                "compute.restart",
            ]
        )

        options: list[ResponseOptionItem] = []
        target_res = affected_resources[0] if affected_resources else "system-service"
        cause_lower = (leading_cause or "").lower()

        # 1. Containment Option (Traffic shed / rate limit) - Highly reversible
        has_contain_cap = "traffic.rate_limit" in caps
        options.append(
            ResponseOptionItem(
                option_id=f"opt_contain_{uuid.uuid4().hex[:6]}",
                title=f"Rate Limit & Shed Traffic on {target_res}",
                strategy_type="contain",
                description="Apply 50% ingress traffic throttle to stabilize resource saturation"
                if has_contain_cap
                else "CAPABILITY_UNAVAILABLE: Rate limiting provider unavailable",
                expected_benefit="Immediate blast radius reduction and memory/CPU stabilization",
                estimated_risk="LOW",
                is_reversible=True,
                requires_approval=False
                if severity in (IncidentSeverity.LOW, IncidentSeverity.MEDIUM)
                else True,
                required_capabilities=["traffic.rate_limit"],
                is_capability_available=has_contain_cap,
                composite_score=0.90 if has_contain_cap else 0.10,
            )
        )

        # 2. Rollback Option (if deployment suspected)
        has_rollback_cap = "deployment.rollback" in caps
        is_deploy_suspect = "deploy" in cause_lower or "commit" in cause_lower
        options.append(
            ResponseOptionItem(
                option_id=f"opt_rollback_{uuid.uuid4().hex[:6]}",
                title=f"Rollback {target_res} to Previous Stable Revision",
                strategy_type="rollback",
                description="Revert container image and config to preceding verified deployment tag"
                if has_rollback_cap
                else "CAPABILITY_UNAVAILABLE: Rollback capability not registered",
                expected_benefit="Eliminates newly introduced regressions and code defects",
                estimated_risk="MEDIUM",
                is_reversible=True,
                requires_approval=True,
                required_capabilities=["deployment.rollback"],
                is_capability_available=has_rollback_cap,
                composite_score=0.95
                if (has_rollback_cap and is_deploy_suspect)
                else (0.75 if has_rollback_cap else 0.10),
            )
        )

        # 3. Scaling Option (Compute / Pod scaling)
        has_scale_cap = "compute.scale" in caps
        options.append(
            ResponseOptionItem(
                option_id=f"opt_scale_{uuid.uuid4().hex[:6]}",
                title=f"Horizontal Pod/Capacity Autoscaling: {target_res}",
                strategy_type="scale",
                description="Add 3 standby replicas to handle load pressure"
                if has_scale_cap
                else "CAPABILITY_UNAVAILABLE: Scaling provider not configured",
                expected_benefit="Absorbs traffic surge and relieves memory/CPU exhaustion",
                estimated_risk="LOW",
                is_reversible=True,
                requires_approval=False if severity != IncidentSeverity.CRITICAL else True,
                required_capabilities=["compute.scale"],
                is_capability_available=has_scale_cap,
                composite_score=0.88 if has_scale_cap else 0.10,
            )
        )

        # 4. Failover Option (Standby provider routing)
        has_failover_cap = "routing.failover" in caps
        options.append(
            ResponseOptionItem(
                option_id=f"opt_failover_{uuid.uuid4().hex[:6]}",
                title=f"Failover Traffic to Standby Secondary Provider for {target_res}",
                strategy_type="failover",
                description="Reroute active traffic to secondary standby availability zone"
                if has_failover_cap
                else "CAPABILITY_UNAVAILABLE: Secondary standby routing unavailable",
                expected_benefit="Completely bypasses impaired primary infrastructure",
                estimated_risk="HIGH",
                is_reversible=True,
                requires_approval=True,
                required_capabilities=["routing.failover"],
                is_capability_available=has_failover_cap,
                composite_score=0.80 if has_failover_cap else 0.10,
            )
        )

        # Sort options descending by composite suitability score
        options.sort(key=lambda o: (o.is_capability_available, o.composite_score), reverse=True)

        logger.info("RESPONSE_OPTIONS_GENERATED: incident=%s count=%d", incident_id, len(options))
        return options


response_option_engine = ResponseOptionEngine()
