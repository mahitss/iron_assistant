"""Unit and integration tests for task requirement extraction, multi-factor scoring, and candidate ranking (Task 59)."""


from app.orchestration.capabilities import create_capability
from app.orchestration.capability_registry import CapabilityRegistry
from app.orchestration.matching import CapabilityMatcher
from app.orchestration.schemas import (
    RiskSeverity,
    TaskCapabilityRequirement,
)


def test_extract_task_requirements():
    """Verify requirements are properly extracted, sanitized, and capabilities inferred."""
    matcher = CapabilityMatcher()
    task = {
        "id": "task_101",
        "title": "Deploy API service to production cluster",
        "environment": "production",
        "required_permissions": ["deploy.production"],
        "is_irreversible": True,
        "priority": 5,
    }
    req = matcher.extract_task_requirements(task)
    assert req.task_id == "task_101"
    assert "deploy_service" in req.required_capabilities
    assert req.environment == "production"
    assert req.is_irreversible is True
    assert req.priority == 5


def test_capability_vs_authorization():
    """Test Invariant 1: Capability != Authorization.

    A provider with the required capability but without granted permissions is marked NOT authorized.
    """
    cap_reg = CapabilityRegistry()
    cap = create_capability(
        name="deploy_service",
        provider="ProdDeployer",
        supported_environments=["production"],
        required_permissions=["deploy.production"],
    )
    cap_reg.register(cap)
    matcher = CapabilityMatcher(cap_reg)

    req = TaskCapabilityRequirement(
        task_id="task_dep_01",
        required_capabilities=["deploy_service"],
        environment="production",
        required_permissions=["deploy.production"],
    )

    # 1. When permission is NOT granted
    score_unauth = matcher.score_candidate(req, cap, granted_permissions=set())
    assert score_unauth.is_authorized is False
    assert "deploy.production" in score_unauth.missing_permissions
    assert score_unauth.overall_score == 0.0  # Blocked from execution

    # 2. When permission IS granted
    score_auth = matcher.score_candidate(req, cap, granted_permissions={"deploy.production"})
    assert score_auth.is_authorized is True
    assert score_auth.overall_score > 0.5


def test_environment_compatibility_gating():
    """Verify development-only capability cannot be matched in production."""
    cap_reg = CapabilityRegistry()
    dev_cap = create_capability(
        name="run_tests",
        provider="LocalDevRunner",
        supported_environments=["development"],  # Only dev
    )
    cap_reg.register(dev_cap)
    matcher = CapabilityMatcher(cap_reg)

    req_prod = TaskCapabilityRequirement(
        task_id="task_test_prod",
        required_capabilities=["run_tests"],
        environment="production",
    )

    score = matcher.score_candidate(req_prod, dev_cap)
    assert score.environment_compatibility is False
    assert score.overall_score == 0.0


def test_candidate_ranking_with_historical_performance():
    """Verify candidate ranking evaluates reliability, cost, risk, and verified historical statistics."""
    cap_reg = CapabilityRegistry()
    cap_a = create_capability(
        name="calculate",
        provider="MathAgentAlpha",
        reliability=0.99,
        latency_ms=10.0,
        cost_estimate=0.01,
        risk_level=RiskSeverity.LOW,
    )
    cap_b = create_capability(
        name="calculate",
        provider="MathAgentBeta",
        reliability=0.80,
        latency_ms=200.0,
        cost_estimate=0.05,
        risk_level=RiskSeverity.MEDIUM,
    )
    cap_reg.register(cap_a)
    cap_reg.register(cap_b)

    matcher = CapabilityMatcher(cap_reg)
    req = TaskCapabilityRequirement(
        task_id="task_calc",
        required_capabilities=["calculate"],
        environment="development",
    )

    ranked = matcher.rank_candidates(req)
    assert len(ranked) == 2
    # Alpha has higher reliability, lower latency, lower cost -> ranks first
    assert ranked[0].provider_name == "MathAgentAlpha"
    assert ranked[0].overall_score > ranked[1].overall_score
