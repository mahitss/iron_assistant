"""Unit tests for Deterministic 5-Tier Risk Engine (Task 36, Specs 33-42, 120, 123)."""

import pytest
from app.policy.risk import DeterministicRiskEngine
from app.policy.schemas import PolicyContext, RiskLevel


def test_read_only_action_classification():
    ctx = PolicyContext(action="get_system_metrics", environment="development")
    risk, factors = DeterministicRiskEngine.evaluate_risk(ctx)
    assert risk == RiskLevel.R0_READ_ONLY
    assert any("read_only" in f for f in factors)


def test_low_risk_action_classification():
    ctx = PolicyContext(action="scroll", environment="development")
    risk, factors = DeterministicRiskEngine.evaluate_risk(ctx)
    assert risk == RiskLevel.R1_LOW


def test_interactive_moderate_action_classification():
    ctx = PolicyContext(action="click", environment="development")
    risk, factors = DeterministicRiskEngine.evaluate_risk(ctx)
    assert risk == RiskLevel.R2_MODERATE


def test_destructive_critical_classification():
    ctx = PolicyContext(action="delete_database", environment="development")
    risk, factors = DeterministicRiskEngine.evaluate_risk(ctx)
    assert risk == RiskLevel.R4_CRITICAL
    assert any("destructive" in f for f in factors)


def test_production_environment_escalation():
    # A moderate click in dev is R2, but mutating in production escalates to R3/R4
    ctx_dev = PolicyContext(action="modify_config", environment="development")
    risk_dev, _ = DeterministicRiskEngine.evaluate_risk(ctx_dev)

    ctx_prod = PolicyContext(action="modify_config", environment="production")
    risk_prod, factors_prod = DeterministicRiskEngine.evaluate_risk(ctx_prod)

    assert risk_prod.severity > risk_dev.severity
    assert risk_prod in (RiskLevel.R3_HIGH, RiskLevel.R4_CRITICAL)
    assert any("production" in f for f in factors_prod)


def test_financial_operation_strictly_critical():
    ctx = PolicyContext(action="transfer_funds", target={"amount": 500})
    risk, factors = DeterministicRiskEngine.evaluate_risk(ctx)
    assert risk == RiskLevel.R4_CRITICAL
    assert any("financial" in f for f in factors)


def test_computer_control_granular_hierarchy():
    # Observe -> R1
    ctx_obs = PolicyContext(action="computer_screenshot", tool="computer_screenshot")
    risk_obs, _ = DeterministicRiskEngine.evaluate_risk(ctx_obs)
    assert risk_obs == RiskLevel.R1_LOW

    # Click -> R2
    ctx_click = PolicyContext(action="computer_click", tool="computer_click")
    risk_click, _ = DeterministicRiskEngine.evaluate_risk(ctx_click)
    assert risk_click == RiskLevel.R2_MODERATE

    # Typing / Form input -> R3
    ctx_type = PolicyContext(action="computer_type", tool="computer_type")
    risk_type, _ = DeterministicRiskEngine.evaluate_risk(ctx_type)
    assert risk_type == RiskLevel.R3_HIGH

    # System settings change -> R4
    ctx_sys = PolicyContext(action="computer_system_settings", tool="computer_type")
    risk_sys, _ = DeterministicRiskEngine.evaluate_risk(ctx_sys)
    assert risk_sys == RiskLevel.R4_CRITICAL


def test_large_blast_radius_escalates():
    ctx_single = PolicyContext(action="update", target={"blast_radius": "single_file"})
    risk_single, _ = DeterministicRiskEngine.evaluate_risk(ctx_single)

    ctx_multi = PolicyContext(action="update", target={"blast_radius": "multi_project"})
    risk_multi, factors_multi = DeterministicRiskEngine.evaluate_risk(ctx_multi)

    assert risk_multi.severity >= risk_single.severity
    assert risk_multi == RiskLevel.R4_CRITICAL
    assert any("large_blast_radius" in f for f in factors_multi)


def test_restricted_data_escalates_to_critical():
    ctx = PolicyContext(action="analyze", data_scope={"classification": "RESTRICTED"})
    risk, factors = DeterministicRiskEngine.evaluate_risk(ctx)
    assert risk == RiskLevel.R4_CRITICAL
    assert any("RESTRICTED" in f for f in factors)
