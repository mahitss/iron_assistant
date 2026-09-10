"""Authorization and policy requirement checks for hypothetical scenarios.

Enforces:
1. Simulation of authorization does NOT grant authorization.
2. Passing simulation does NOT equal approval (Prompt #63).
3. Self-authorization is strictly prohibited.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.simulation.schemas import SimulatedIntervention


class AuthorizationRequirement(BaseModel):
    """Identifies permissions, roles, or approvals needed for a hypothetical change."""

    operation: str
    target: str
    required_role: str
    requires_human_approval: bool
    is_high_risk: bool
    policy_rule: str
    approval_reasons: list[str] = Field(default_factory=list)


class SimulationAuthorizationChecker:
    """Evaluates whether hypothetical actions require elevated privileges or human approval."""

    HIGH_RISK_OPERATIONS = frozenset({
        "KILL_SERVICE",
        "FAILOVER_DATABASE",
        "SCHEMA_MIGRATION",
        "DROP_TABLE",
        "MODIFY_PERMISSIONS",
        "NETWORK_DISCONNECT",
    })

    def check_requirements(
        self,
        interventions: list[SimulatedIntervention],
    ) -> list[AuthorizationRequirement]:
        """Audits hypothetical interventions to identify necessary production approvals."""
        requirements: list[AuthorizationRequirement] = []

        for interv in interventions:
            op = interv.operation.upper()
            is_high_risk = any(hr in op for hr in self.HIGH_RISK_OPERATIONS)
            needs_approval = is_high_risk or ("SCALE" in op and interv.hypothetical_after.get("replicas", 0) > 10)

            reasons = []
            if is_high_risk:
                reasons.append(f"Operation '{op}' is classified as HIGH_RISK infrastructure mutation.")
            if needs_approval and not is_high_risk:
                reasons.append("Resource quota scaling threshold exceeded.")

            requirements.append(
                AuthorizationRequirement(
                    operation=op,
                    target=interv.target,
                    required_role="admin" if is_high_risk else "operator",
                    requires_human_approval=needs_approval,
                    is_high_risk=is_high_risk,
                    policy_rule="infra.security.mutation_gate",
                    approval_reasons=reasons,
                )
            )

        return requirements
