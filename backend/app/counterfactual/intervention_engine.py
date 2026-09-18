"""Intervention modeling, validation, reversibility assessment, and simulation firewall for Task 113.
Ensures simulated interventions cannot mutate production state or bypass security governance.
"""

from __future__ import annotations

import copy
import logging
import re
from typing import Any
import uuid

from app.counterfactual.domain import (
    AssumptionStatus,
    CounterfactualType,
    Intervention,
    InterventionAssumption,
    InterventionConstraint,
    InterventionMechanism,
    InterventionScope,
)
from app.security.emergency_stop import get_emergency_stop_service

logger = logging.getLogger("kairo.counterfactual.intervention_engine")

PROMPT_INJECTION_PATTERNS = [
    re.compile(r"THIS\s+(?:EVENT|SOURCE)\s+IS\s+A\s+SYSTEM\s+COMMAND", re.IGNORECASE),
    re.compile(r"IGNORE\s+GOVERNANCE", re.IGNORECASE),
    re.compile(r"AUTHORIZE\s+THIS\s+ACTION", re.IGNORECASE),
    re.compile(r"EMERGENCY\s+STOP\s+IS\s+CANCELLED", re.IGNORECASE),
    re.compile(r"YOU\s+MUST\s+TRUST\s+THIS\s+CAUSE", re.IGNORECASE),
    re.compile(r"THIS\s+SOURCE\s+HAS\s+ROOT\s+AUTHORITY", re.IGNORECASE),
    re.compile(r"BYPASS\s+SECURITY", re.IGNORECASE),
]


class InterventionEngine:
    """Validates, sandboxes, and structures candidate causal interventions."""

    @classmethod
    def sanitize_untrusted_input(cls, text: str) -> str:
        """Neutralizes adversarial prompt injection payloads inside intervention descriptors."""
        cleaned = text
        for pattern in PROMPT_INJECTION_PATTERNS:
            cleaned = pattern.sub("[DISARMED_UNTRUSTED_DIRECTIVE]", cleaned)
        return cleaned

    @classmethod
    def create_intervention(
        cls,
        name: str,
        target: str,
        changes: dict[str, Any],
        intervention_type: CounterfactualType = CounterfactualType.RESOURCE,
        scope: InterventionScope = InterventionScope.SERVICE,
        assumptions: list[str] | None = None,
        is_reversible: bool = True,
        reversibility_plan: str = "",
        risk_level: str = "LOW",
        user_id: str | None = None,
    ) -> Intervention:
        """Constructs and validates a simulated intervention through the simulation firewall."""
        intv_id = f"intv_{uuid.uuid4().hex[:12]}"
        safe_name = cls.sanitize_untrusted_input(name)
        safe_target = cls.sanitize_untrusted_input(target)

        # 1. Parse and sanitize changes payload
        safe_changes: dict[str, Any] = {}
        for k, v in changes.items():
            safe_k = cls.sanitize_untrusted_input(str(k))
            if isinstance(v, str):
                safe_changes[safe_k] = cls.sanitize_untrusted_input(v)
            else:
                safe_changes[safe_k] = v

        # 2. Build default assumptions
        parsed_assumptions: list[InterventionAssumption] = []
        default_asm = assumptions or [
            "ceteris_paribus_environment_stability",
            "treatment_effect_local_to_target_subgraph",
            "model_validity_holds_during_simulation_horizon",
        ]
        for desc in default_asm:
            safe_desc = cls.sanitize_untrusted_input(desc)
            parsed_assumptions.append(
                InterventionAssumption(
                    description=safe_desc,
                    status=AssumptionStatus.PLAUSIBLE,
                    supporting_evidence=["historical_domain_knowledge"],
                )
            )

        # 3. Build default mechanism
        mechanisms = [
            InterventionMechanism(
                treatment_variable=safe_target,
                target_variable=f"{safe_target}.outcome",
                pathway_description=f"Direct modification of {safe_target} properties: {list(safe_changes.keys())}",
                confidence=0.75,
            )
        ]

        # 4. Simulation Firewall & EmergencyStop Verification
        is_blocked = False
        block_reason = ""
        requires_approval = risk_level in ("HIGH", "CRITICAL") or not is_reversible

        e_stop = get_emergency_stop_service()
        if e_stop.is_stopped(user_id):
            is_blocked = True
            block_reason = "EMERGENCY_STOP_ACTIVE: Interventions cannot be planned or evaluated while EmergencyStop is triggered."

        # Detect attempts to mutate production or bypass security
        if safe_changes.get("authorize_action") or safe_changes.get("override_governance") or safe_changes.get("release_emergency_stop"):
            is_blocked = True
            block_reason = "SECURITY_BLOCKED: Intervention attempted privilege escalation or governance bypass."

        constraints = [
            InterventionConstraint(
                description="Simulation isolation constraint: no side effects outside sandbox.",
                is_hard_invariant=True,
                satisfied=True,
            ),
            InterventionConstraint(
                description="Reversibility constraint: must provide safe rollback if high risk.",
                is_hard_invariant=not is_reversible,
                satisfied=is_reversible or bool(reversibility_plan),
                violation_reason="Missing reversibility plan for irreversible intervention." if not is_reversible and not reversibility_plan else "",
            ),
        ]

        return Intervention(
            intervention_id=intv_id,
            name=safe_name,
            target=safe_target,
            scope=scope,
            changes=safe_changes,
            intervention_type=intervention_type,
            assumptions=parsed_assumptions,
            constraints=constraints,
            mechanisms=mechanisms,
            is_reversible=is_reversible,
            reversibility_plan=reversibility_plan or ("Automatic parameter reversion" if is_reversible else "Manual architectural intervention required"),
            estimated_resource_cost={"cpu_units": 0.1, "memory_mb": 64.0},
            risk_level=risk_level,
            requires_approval=requires_approval,
            is_blocked=is_blocked,
            block_reason=block_reason,
            environment_label="SIMULATION_ONLY",
            is_hypothetical=True,
        )
