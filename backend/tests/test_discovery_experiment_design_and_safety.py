"""Unit tests for Experiment Design, Safety Gating, and Risk Assessment (Task 72)."""

from app.discovery.design import ExperimentDesigner
from app.discovery.schemas import (
    EnvironmentType,
    ExperimentType,
    RiskLevel,
    RollbackPlan,
)


def test_experiment_risk_assessment_read_only_types():
    """Observational and Simulation experiments are safe or low risk."""
    designer = ExperimentDesigner()

    # Simulation in simulation environment -> SAFE, no authorization required
    risk, auth = designer.assess_risk(
        experiment_type=ExperimentType.SIMULATION,
        environment=EnvironmentType.SIMULATION,
        is_mutable=False,
        has_rollback=False,
    )
    assert risk == RiskLevel.SAFE
    assert not auth

    # Observational in staging -> LOW_RISK, no authorization required
    risk, auth = designer.assess_risk(
        experiment_type=ExperimentType.OBSERVATIONAL,
        environment=EnvironmentType.STAGING,
        is_mutable=False,
        has_rollback=False,
    )
    assert risk == RiskLevel.LOW_RISK
    assert not auth


def test_experiment_risk_production_and_canary():
    """Any experiment in Production or Canary is CRITICAL_RISK and requires human authorization."""
    designer = ExperimentDesigner()

    risk, auth = designer.assess_risk(
        experiment_type=ExperimentType.CONTROLLED,
        environment=EnvironmentType.PRODUCTION,
        is_mutable=True,
        has_rollback=True,
    )
    assert risk == RiskLevel.CRITICAL_RISK
    assert auth is True

    risk, auth = designer.assess_risk(
        experiment_type=ExperimentType.AB,
        environment=EnvironmentType.CANARY,
        is_mutable=True,
        has_rollback=True,
    )
    assert risk == RiskLevel.CRITICAL_RISK
    assert auth is True


def test_experiment_missing_rollback_elevates_risk():
    """Mutable trials missing a rollback plan elevate risk and require authorization."""
    designer = ExperimentDesigner()

    # Staging mutable with rollback -> MEDIUM_RISK, auth required
    risk, auth = designer.assess_risk(
        experiment_type=ExperimentType.CONTROLLED,
        environment=EnvironmentType.STAGING,
        is_mutable=True,
        has_rollback=True,
    )
    assert risk == RiskLevel.MEDIUM_RISK
    assert auth is True

    # Test environment mutable WITHOUT rollback -> HIGH_RISK, auth required
    risk, auth = designer.assess_risk(
        experiment_type=ExperimentType.CONTROLLED,
        environment=EnvironmentType.TEST,
        is_mutable=True,
        has_rollback=False,
    )
    assert risk == RiskLevel.HIGH_RISK
    assert auth is True


def test_select_least_risky_experiment():
    """Strict principle: Use the least risky experiment that provides sufficient information."""
    designer = ExperimentDesigner()

    # Trial 1: High risk in production with 90% information gain
    exp_prod = designer.design_experiment(
        discovery_id="disc_1",
        hypothesis_ids=["h1"],
        objective="Test config directly in production",
        experiment_type=ExperimentType.CONTROLLED,
        environment=EnvironmentType.PRODUCTION,
        expected_information_gain=0.90,
    )

    # Trial 2: Low risk in staging with 85% information gain
    exp_staging = designer.design_experiment(
        discovery_id="disc_1",
        hypothesis_ids=["h1"],
        objective="Test config safely in staging with synthetic replay",
        experiment_type=ExperimentType.OBSERVATIONAL,
        environment=EnvironmentType.STAGING,
        expected_information_gain=0.85,
    )

    # Safety takes precedence: Designer must select staging over production
    selected = designer.select_least_risky_experiment([exp_prod, exp_staging])
    assert selected is not None
    assert selected.experiment_id == exp_staging.experiment_id
    assert selected.environment == EnvironmentType.STAGING
    assert selected.risk_level in {RiskLevel.SAFE, RiskLevel.LOW_RISK}


def test_experiment_design_reproducibility_and_variables():
    """Verifies complete variable tracking (independent, dependent, controls, confounders)."""
    designer = ExperimentDesigner()

    exp = designer.design_experiment(
        discovery_id="disc_test",
        hypothesis_ids=["hyp_1", "hyp_2"],
        objective="Evaluate pool timeout effect on tail latency",
        experiment_type=ExperimentType.CONTROLLED,
        environment=EnvironmentType.STAGING,
        independent_variables={"connection_timeout_ms": 5000},
        dependent_variables=["p95_latency_ms", "5xx_error_rate"],
        control_variables={"traffic_profile": "steady_100_rps", "concurrency": 20},
        potential_confounders=["background_gc_cycles", "database_checkpointing"],
        baseline={"p95_latency_ms": 320, "5xx_error_rate": 0.04},
        rollback_plan=RollbackPlan(
            rollback_action="revert_connection_timeout_ms_to_2000",
            rollback_owner="SRE_Agent",
            rollback_timeout_sec=30,
            rollback_verification="verify_p95_latency_baseline",
        ),
    )

    assert exp.independent_variables["connection_timeout_ms"] == 5000
    assert "p95_latency_ms" in exp.dependent_variables
    assert exp.control_variables["traffic_profile"] == "steady_100_rps"
    assert "background_gc_cycles" in exp.potential_confounders
    assert exp.baseline["p95_latency_ms"] == 320
    assert exp.rollback_plan.rollback_action.startswith("revert_")
