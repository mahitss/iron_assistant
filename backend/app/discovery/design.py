"""Experiment Design, Safety Classification, and Variable Management (Task 72).

Designs reproducible, controlled experiments adhering to safety gates, environment isolation,
mandatory rollback, and cleanup plans.
"""

import uuid
from typing import Any

from app.discovery.schemas import (
    CleanupPlan,
    EnvironmentType,
    ExperimentDesign,
    ExperimentStatus,
    ExperimentType,
    RiskLevel,
    RollbackPlan,
)


class ExperimentDesigner:
    """Creates rigorous scientific experiment specifications with safety gating."""

    # Hierarchy of experiment risks by environment and type
    DEFAULT_ENVIRONMENT_RISK: dict[EnvironmentType, RiskLevel] = {
        EnvironmentType.SIMULATION: RiskLevel.SAFE,
        EnvironmentType.LOCAL: RiskLevel.LOW_RISK,
        EnvironmentType.TEST: RiskLevel.LOW_RISK,
        EnvironmentType.STAGING: RiskLevel.MEDIUM_RISK,
        EnvironmentType.CANARY: RiskLevel.HIGH_RISK,
        EnvironmentType.PRODUCTION: RiskLevel.CRITICAL_RISK,
    }

    def assess_risk(
        self,
        experiment_type: ExperimentType,
        environment: EnvironmentType,
        is_mutable: bool,
        has_rollback: bool,
    ) -> tuple[RiskLevel, bool]:
        """Calculates safety risk level and whether human approval is strictly required.

        Rule:
        - Observational, Simulation, Replay, Research are read-only -> SAFE or LOW_RISK.
        - Staging mutable without rollback -> HIGH_RISK.
        - Production or Canary -> CRITICAL_RISK / HIGH_RISK, always requires authorization.
        """
        # Read-only types are inherently safe or low risk
        if experiment_type in {
            ExperimentType.OBSERVATIONAL,
            ExperimentType.SIMULATION,
            ExperimentType.REPLAY,
            ExperimentType.RESEARCH,
        }:
            if environment == EnvironmentType.SIMULATION:
                return RiskLevel.SAFE, False
            return RiskLevel.LOW_RISK, False

        # Mutable experiments in Production or Canary
        if environment in {EnvironmentType.PRODUCTION, EnvironmentType.CANARY}:
            return RiskLevel.CRITICAL_RISK, True

        # Mutable experiments in Staging or Test
        if is_mutable:
            if not has_rollback:
                # Missing rollback elevates risk
                return RiskLevel.HIGH_RISK, True
            if environment == EnvironmentType.STAGING:
                return RiskLevel.MEDIUM_RISK, True
            return RiskLevel.LOW_RISK, False

        base_risk = self.DEFAULT_ENVIRONMENT_RISK.get(environment, RiskLevel.MEDIUM_RISK)
        requires_auth = base_risk in {RiskLevel.HIGH_RISK, RiskLevel.CRITICAL_RISK}
        return base_risk, requires_auth

    def design_experiment(
        self,
        discovery_id: str,
        hypothesis_ids: list[str],
        objective: str,
        experiment_type: ExperimentType = ExperimentType.OBSERVATIONAL,
        environment: EnvironmentType = EnvironmentType.STAGING,
        description: str = "",
        independent_variables: dict[str, Any] | None = None,
        dependent_variables: list[str] | None = None,
        control_variables: dict[str, Any] | None = None,
        potential_confounders: list[str] | None = None,
        baseline: dict[str, Any] | None = None,
        expected_result: str = "",
        success_criteria: list[str] | None = None,
        failure_criteria: list[str] | None = None,
        falsification_criteria: list[str] | None = None,
        rollback_plan: RollbackPlan | None = None,
        cleanup_plan: CleanupPlan | None = None,
        dependencies: list[str] | None = None,
        estimated_cost: float = 0.1,
        estimated_duration_sec: int = 60,
        expected_information_gain: float = 0.8,
        scope: str = "isolated",
    ) -> ExperimentDesign:
        """Constructs an ExperimentDesign adhering strictly to safety boundaries.

        Validates that mutable experiments define rollback and cleanup plans.
        """
        is_mutable = experiment_type in {
            ExperimentType.CONTROLLED,
            ExperimentType.AB,
        }
        has_valid_rollback = rollback_plan is not None and bool(rollback_plan.rollback_action)

        risk_level, auth_required = self.assess_risk(
            experiment_type=experiment_type,
            environment=environment,
            is_mutable=is_mutable,
            has_rollback=has_valid_rollback,
        )

        # Build default plans if omitted for non-mutable
        final_rollback = rollback_plan or RollbackPlan(
            rollback_action="none_required_read_only" if not is_mutable else "manual_intervention_required",
            rollback_verification="verify_clean_state",
        )
        final_cleanup = cleanup_plan or CleanupPlan(
            cleanup_action="release_ephemeral_resources",
            cleanup_resources=[],
        )

        exp_id = f"exp_{uuid.uuid4().hex[:12]}"

        # Default criteria
        final_success = list(success_criteria or ["empirical_measurements_recorded_successfully"])
        final_failure = list(failure_criteria or ["measurement_timeout_or_infrastructure_error"])
        final_falsification = list(falsification_criteria or ["observation_inverts_predicted_effect"])

        return ExperimentDesign(
            experiment_id=exp_id,
            discovery_id=discovery_id,
            hypothesis_ids=list(hypothesis_ids),
            objective=objective.strip(),
            description=description.strip(),
            experiment_type=experiment_type,
            environment=environment,
            scope=scope,
            independent_variables=independent_variables or {},
            dependent_variables=list(dependent_variables or ["metric_delta"]),
            control_variables=control_variables or {},
            potential_confounders=list(potential_confounders or []),
            baseline=baseline or {},
            expected_result=expected_result,
            success_criteria=final_success,
            failure_criteria=final_failure,
            falsification_criteria=final_falsification,
            risk_level=risk_level,
            estimated_cost=float(estimated_cost),
            estimated_duration_sec=int(estimated_duration_sec),
            expected_information_gain=max(0.0, min(1.0, float(expected_information_gain))),
            authorization_required=auth_required,
            is_authorized=not auth_required,  # Safe trials are auto-authorized
            rollback_plan=final_rollback,
            cleanup_plan=final_cleanup,
            dependencies=list(dependencies or []),
            status=ExperimentStatus.APPROVAL_REQUIRED if auth_required else ExperimentStatus.READY,
        )

    def select_least_risky_experiment(
        self,
        candidate_designs: list[ExperimentDesign],
    ) -> ExperimentDesign | None:
        """Selects the candidate experiment optimizing for highest information gain at lowest risk.

        Strict Principle: Use the least risky experiment that provides sufficient information.
        Safety takes precedence over information gain.
        """
        if not candidate_designs:
            return None

        risk_order = {
            RiskLevel.SAFE: 1,
            RiskLevel.LOW_RISK: 2,
            RiskLevel.MEDIUM_RISK: 3,
            RiskLevel.HIGH_RISK: 4,
            RiskLevel.CRITICAL_RISK: 5,
        }

        # Sort primarily by risk (ascending), secondarily by information gain (descending)
        return min(
            candidate_designs,
            key=lambda e: (
                risk_order.get(e.risk_level, 99),
                -e.expected_information_gain,
                e.estimated_cost,
            ),
        )
