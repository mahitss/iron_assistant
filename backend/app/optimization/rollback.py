"""Automated rollback execution, state reconciliation, and restoration verification (Task 62)."""

from __future__ import annotations

import logging

from app.optimization.parameters import AdjustableParameterRegistry, adjustable_parameter_registry
from app.optimization.safety import OptimizationSafetyError
from app.optimization.schemas import (
    ChangeSet,
    ChangeSetStatus,
    RollbackPlan,
)

logger = logging.getLogger(__name__)


class RollbackManager:
    """Executes safe parameter rollbacks and performs mandatory post-rollback verification.

    Invariant 22 & 23: Rollback executed != rollback successful. The system must verify
    that the target parameter was actually restored to its verified pre-change baseline.
    """

    def __init__(self, registry: AdjustableParameterRegistry | None = None) -> None:
        self._registry = registry or adjustable_parameter_registry
        self._rollbacks: dict[str, RollbackPlan] = {}

    def execute_rollback(
        self,
        change_set: ChangeSet,
        reason: str = "Rollback triggered",
    ) -> RollbackPlan:
        """Revert change set parameter and verify restored state."""
        param_name = change_set.target_parameter
        restoration_val = change_set.before_state

        plan = RollbackPlan(
            change_set_id=change_set.change_set_id,
            target_parameter=param_name,
            restoration_value=restoration_val,
            is_executed=False,
            is_verified=False,
        )

        param = self._registry.get_parameter(param_name)
        if not param:
            raise OptimizationSafetyError(
                f"ROLLBACK_FAILED: Target parameter '{param_name}' not found in registry."
            )

        # 1. Execute parameter restoration
        self._registry.apply_value(param_name, restoration_val)
        plan.is_executed = True

        # 2. Mandatory Verification check: Read back to confirm real state restored
        updated_param = self._registry.get_parameter(param_name)
        if updated_param and abs(updated_param.current_value - restoration_val) < 1e-5:
            plan.is_verified = True
            plan.reconciled_state = {
                "parameter": param_name,
                "verified_value": updated_param.current_value,
                "nominal_baseline_restored": True,
            }
            change_set.status = ChangeSetStatus.REVERTED
            logger.info(
                "ROLLBACK_VERIFIED: change_set=%s param=%s restored to %.4f",
                change_set.change_set_id,
                param_name,
                restoration_val,
            )
        else:
            plan.is_verified = False
            change_set.status = ChangeSetStatus.FAILED
            logger.error(
                "ROLLBACK_VERIFICATION_FAILED: change_set=%s expected=%.4f actual=%.4f",
                change_set.change_set_id,
                restoration_val,
                updated_param.current_value if updated_param else -1,
            )

        self._rollbacks[plan.rollback_id] = plan
        return plan

    def get_rollback(self, rollback_id: str) -> RollbackPlan | None:
        """Retrieve rollback plan by ID."""
        return self._rollbacks.get(rollback_id)


rollback_manager = RollbackManager()
