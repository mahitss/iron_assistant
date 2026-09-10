"""Unit tests for Mitigation Preparation, Containment, and Action Gating (Task 61)."""

import pytest

from app.incident_response.mitigation import MitigationEngine
from app.incident_response.schemas import (
    ActionState,
    ResponseOptionItem,
)


def test_prepare_mitigation_action_success():
    """Verify that a capable response option prepares an idempotent, reversible mitigation action."""
    engine = MitigationEngine()

    opt = ResponseOptionItem(
        option_id="opt_test_rate_limit",
        title="Apply ingress rate limiting",
        strategy_type="contain",
        description="Throttle incoming requests by 50%",
        expected_benefit="Stabilize queue depth",
        estimated_risk="LOW",
        is_reversible=True,
        requires_approval=False,
        is_capability_available=True,
    )

    action = engine.prepare_mitigation_action(
        incident_id="inc_mit_01",
        option=opt,
        actor="lead_operator",
        parameters={"rate_limit_per_minute": 500},
    )

    assert action.incident_id == "inc_mit_01"
    assert action.action_type == "MITIGATION_CONTAIN"
    assert action.status == ActionState.AUTHORIZED
    assert action.is_reversible is True
    assert action.is_idempotent is True
    assert action.requires_approval is False


def test_prepare_mitigation_requires_approval():
    """Verify high-impact mitigation options are gated as PROPOSED until explicitly approved."""
    engine = MitigationEngine()

    opt = ResponseOptionItem(
        option_id="opt_test_failover",
        title="Trigger active failover",
        strategy_type="failover",
        description="Reroute traffic to secondary AZ",
        expected_benefit="Bypass primary failure",
        estimated_risk="HIGH",
        is_reversible=True,
        requires_approval=True,
        is_capability_available=True,
    )

    action = engine.prepare_mitigation_action(
        incident_id="inc_mit_02",
        option=opt,
        actor="system_bot",
    )

    assert action.status == ActionState.PROPOSED
    assert action.requires_approval is True


def test_prepare_mitigation_rejects_unavailable_capability():
    """Verify attempting mitigation with an unavailable capability raises ValueError."""
    engine = MitigationEngine()

    opt = ResponseOptionItem(
        option_id="opt_unavail",
        title="Unregistered custom rollback",
        strategy_type="rollback",
        description="CAPABILITY_UNAVAILABLE: Tool missing",
        expected_benefit="Rollback",
        is_capability_available=False,
    )

    with pytest.raises(ValueError, match="capability unavailable"):
        engine.prepare_mitigation_action("inc_mit_03", opt, actor="bot")
