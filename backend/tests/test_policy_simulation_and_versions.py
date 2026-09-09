"""Unit tests for Policy Simulation, Shadow Mode, Versioning, and Rollback (Task 36, Specs 7, 88, 92, 93, 132, 133, 154-156)."""

import pytest
from app.policy.engine import PolicyEngine
from app.policy.registry import PolicyRegistry
from app.policy.schemas import (
    ConditionOperator,
    PolicyContext,
    PolicyCreateRequest,
    PolicyDecisionType,
    PolicyRollbackRequest,
    PolicyRule,
    PolicyRuleCondition,
    PolicyScope,
    PolicySimulationRequest,
    PolicyUpdateRequest,
)


@pytest.mark.asyncio
async def test_policy_simulation_does_not_mutate_state():
    engine = PolicyEngine()
    ctx = PolicyContext(action="deploy", environment="staging")

    req = PolicySimulationRequest(context=ctx)
    sim_res = await engine.simulate(req)

    assert sim_res.decision.simulated is True
    assert sim_res.decision.decision == PolicyDecisionType.ALLOW
    assert len(sim_res.trace) > 0

    # Ensure simulation did not create a real provenance record in history
    eval_id = sim_res.decision.evaluation_id
    # Provenance lookup should return None for simulations
    assert engine.provenance.get_evaluation(eval_id) is None


def test_policy_versioning_and_rollback():
    reg = PolicyRegistry()

    # 1. Create Policy (Version 1)
    req = PolicyCreateRequest(
        policy_id="test-app-policy",
        name="Test Policy V1",
        scope=PolicyScope.GLOBAL,
        decision=PolicyDecisionType.ALLOW,
    )
    p1 = reg.create_policy(req, creator="admin_1")
    assert p1.version == 1

    # 2. Update Policy (Version 2)
    upd = PolicyUpdateRequest(
        name="Test Policy V2",
        decision=PolicyDecisionType.REQUIRE_APPROVAL,
    )
    p2 = reg.update_policy("test-app-policy", upd, updater="admin_2")
    assert p2.version == 2
    assert p2.decision == PolicyDecisionType.REQUIRE_APPROVAL

    # Verify history has both v1 and v2 (Section 7, 132)
    history = reg.get_history("test-app-policy")
    assert len(history) == 2
    assert history[0].version == 1
    assert history[0].decision == PolicyDecisionType.ALLOW
    assert history[1].version == 2
    assert history[1].decision == PolicyDecisionType.REQUIRE_APPROVAL

    # 3. Roll back to Version 1 (Section 154)
    rb_req = PolicyRollbackRequest(target_version=1, reason="Regression detected in V2")
    p3 = reg.rollback_policy("test-app-policy", rb_req, operator="security_admin")
    assert p3.version == 3  # Rollback creates new version carrying v1 config
    assert p3.decision == PolicyDecisionType.ALLOW
    assert "Rolled back to v1" in p3.description


@pytest.mark.asyncio
async def test_shadow_mode_evaluates_without_enforcing():
    engine = PolicyEngine()

    # Register a shadow rule that would normally DENY staging actions
    shadow_rule = PolicyRule(
        policy_id="shadow-staging-deny",
        name="Shadow Staging Restriction",
        version=1,
        enabled=True,
        shadow_mode=True,  # Shadow mode!
        scope=PolicyScope.ENVIRONMENT,
        target_scope_id="staging",
        conditions=[
            PolicyRuleCondition(field="environment", operator=ConditionOperator.EQUALS, value="staging"),
        ],
        decision=PolicyDecisionType.DENY,
    )
    engine.registry.register_policy(shadow_rule)

    ctx = PolicyContext(action="deploy", environment="staging")
    decision = await engine.evaluate(ctx)

    # Active decision should NOT be DENY because shadow rule does not enforce!
    assert decision.decision != PolicyDecisionType.DENY
    # But shadow result is tracked in shadow_decisions list
    assert any(s.get("policy_id") == "shadow-staging-deny" for s in decision.shadow_decisions)


def test_cache_invalidation_on_mutation():
    reg = PolicyRegistry()
    ctx = PolicyContext(action="read", environment="development")
    from app.policy.schemas import PolicyDecision, RiskLevel

    dec = PolicyDecision(
        decision=PolicyDecisionType.ALLOW,
        safe_explanation="OK",
        risk_level=RiskLevel.R0_READ_ONLY,
        evaluation_id="test_cache_1",
    )
    reg.cache_decision(ctx, dec)
    assert reg.cached_count == 1
    assert reg.get_cached_decision(ctx) is not None

    # Invalidate
    reg.invalidate_cache()
    assert reg.cached_count == 0
    assert reg.get_cached_decision(ctx) is None
