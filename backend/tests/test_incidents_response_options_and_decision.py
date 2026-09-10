"""Unit tests for Response Option Generation, Capability Validation, and Reversibility Scoring (Task 61)."""

from app.incident_response.options import ResponseOptionEngine
from app.incident_response.schemas import IncidentSeverity


def test_response_options_generation_and_reversibility():
    """Verify response options are generated with reversibility and approval flags."""
    engine = ResponseOptionEngine()

    options = engine.generate_options(
        incident_id="inc_opt_01",
        severity=IncidentSeverity.HIGH,
        affected_resources=["api-service"],
        leading_cause="Recent deployment rollback suspect",
    )

    assert len(options) >= 3
    strategies = {o.strategy_type for o in options}
    assert "contain" in strategies
    assert "rollback" in strategies
    assert "scale" in strategies

    # Rate limiting / containment must be marked reversible with low risk
    contain_opt = next(o for o in options if o.strategy_type == "contain")
    assert contain_opt.is_reversible is True
    assert contain_opt.estimated_risk == "LOW"


def test_missing_capability_flags_capability_unavailable():
    """Test Invariant 26: No fabricated actions. Missing capabilities are explicitly marked CAPABILITY_UNAVAILABLE."""
    engine = ResponseOptionEngine()

    # Only compute.scale is available; rollback and failover are missing
    options = engine.generate_options(
        incident_id="inc_opt_gap",
        severity=IncidentSeverity.HIGH,
        affected_resources=["legacy-monolith"],
        available_capabilities=["compute.scale"],
    )

    scale_opt = next(o for o in options if o.strategy_type == "scale")
    assert scale_opt.is_capability_available is True

    rollback_opt = next(o for o in options if o.strategy_type == "rollback")
    assert rollback_opt.is_capability_available is False
    assert "CAPABILITY_UNAVAILABLE" in rollback_opt.description

    failover_opt = next(o for o in options if o.strategy_type == "failover")
    assert failover_opt.is_capability_available is False
    assert "CAPABILITY_UNAVAILABLE" in failover_opt.description


def test_approval_requirement_enforced_on_high_severity():
    """Verify that high-impact actions require approval for high/critical severity."""
    engine = ResponseOptionEngine()

    crit_options = engine.generate_options(
        incident_id="inc_crit_opt",
        severity=IncidentSeverity.CRITICAL,
        affected_resources=["core-db"],
    )

    for opt in crit_options:
        # For critical incidents, all major actions require human approval
        if opt.strategy_type in ("rollback", "failover", "scale"):
            assert opt.requires_approval is True
