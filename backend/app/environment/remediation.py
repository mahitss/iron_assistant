"""Remediation Planning, Governed Execution, and Rollback Verification (Task 54, Prompts #107-#114, #218-#225)."""

from __future__ import annotations

import uuid
from typing import Any

from app.environment.safety import ProductionSafetyViolationError, UnverifiedRollbackError
from app.environment.schemas import ImpactLevel, RemediationPlan
from app.environment.temporal import utc_now


class RemediationManager:
    """Constructs structured, verifiable change plans with mandatory rollback specifications."""

    @staticmethod
    def create_change_plan(
        target: str,
        current_state: dict[str, Any],
        desired_state: dict[str, Any],
        risk: ImpactLevel,
        dependencies: list[str],
        rollback_target: dict[str, Any] | None = None,
        rollback_verified: bool = False,
        verification_postconditions: list[str] | None = None,
        is_production: bool = False,
    ) -> RemediationPlan:
        """Prompt #110, #112, #220: Show/record target, current, desired, risk, rollback, verification."""
        # Prompt #110, #111: Rollback requires verified rollback target
        if is_production and (not rollback_target or not rollback_verified):
            raise UnverifiedRollbackError(
                "Production remediation plans require an explicit and pre-verified rollback target."
            )

        pid = f"plan_{uuid.uuid4().hex[:10]}"
        return RemediationPlan(
            plan_id=pid,
            target=target,
            current_state=current_state,
            desired_state=desired_state,
            risk=risk,
            dependencies=dependencies,
            rollback_target=rollback_target,
            rollback_verified=rollback_verified,
            verification_postconditions=verification_postconditions or ["health_check == HEALTHY"],
            approved=False,
            status="PROPOSED",
            created_at=utc_now(),
        )

    @staticmethod
    def validate_plan_for_execution(
        plan: RemediationPlan,
        is_production: bool,
        current_observed_state: dict[str, Any],
    ) -> None:
        """Prompt #129, #130: Revalidate state immediately before consequential action to prevent state races."""
        if is_production and not plan.approved:
            raise ProductionSafetyViolationError(
                f"Remediation plan '{plan.plan_id}' on production has not been approved."
            )

        # Prompt #129, #130: Stale plan detection
        for k, v in plan.current_state.items():
            if current_observed_state.get(k) != v:
                raise ProductionSafetyViolationError(
                    f"State race detected: Current state of '{k}' changed since plan was generated. Replanning required."
                )
