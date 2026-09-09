"""Tests for SkillResolver, deterministic intent matching, capability pruning, and SkillPlanner."""

import pytest
from app.security.center import SecurityCenter
from app.security.permissions import Capability
from app.skills.catalog import create_default_skills
from app.skills.planner import SkillPlanner
from app.skills.registry import SkillRegistry
from app.skills.resolver import SkillResolver


@pytest.fixture
def registry_with_skills() -> SkillRegistry:
    """Provide registry populated with canonical built-in skills."""
    reg = SkillRegistry()
    for skill in create_default_skills():
        reg.register(skill)
    return reg


@pytest.fixture
def security_center() -> SecurityCenter:
    """Provide SecurityCenter with default active capabilities."""
    return SecurityCenter()


@pytest.fixture
def resolver(registry_with_skills: SkillRegistry, security_center: SecurityCenter) -> SkillResolver:
    """Provide a SkillResolver attached to the populated registry and SecurityCenter."""
    return SkillResolver(registry_with_skills, security_center=security_center)


@pytest.fixture
def planner() -> SkillPlanner:
    """Provide a SkillPlanner."""
    return SkillPlanner()


def test_resolver_explicit_skill_id(resolver: SkillResolver) -> None:
    """Ensure explicit skill ID bypasses fuzzy matching and resolves directly."""
    resolved = resolver.resolve(
        query="Any arbitrary text",
        explicit_skill_id="research.web",
    )
    assert resolved is not None
    assert resolved.id == "research.web"


def test_resolver_deterministic_ci_failure_intent(resolver: SkillResolver) -> None:
    """Ensure 'Find why CI failed' resolves to developer.repository or github.analysis deterministically (Section 7 & 8)."""
    resolved = resolver.resolve(
        query="Find why CI failed and test build broke",
        project_id="proj_kairo",
    )
    assert resolved is not None
    assert resolved.id in ("developer.repository", "github.analysis")


def test_resolver_deterministic_web_research_intent(resolver: SkillResolver) -> None:
    """Ensure web search requests resolve to research.web without calling LLM."""
    resolved = resolver.resolve(
        query="Research the latest documentation about Python 3.14 features on the web",
    )
    assert resolved is not None
    assert resolved.id == "research.web"


def test_resolver_deterministic_knowledge_intent(resolver: SkillResolver) -> None:
    """Ensure knowledge fabric search resolves to knowledge.search."""
    resolved = resolver.resolve(
        query="Search knowledge fabric memory for architecture decisions",
        project_id="proj_kairo",
    )
    assert resolved is not None
    assert resolved.id == "knowledge.search"


def test_resolver_deterministic_automation_intent(resolver: SkillResolver) -> None:
    """Ensure automation management resolves to automation.manage."""
    resolved = resolver.resolve(
        query="Create a daily workflow that checks CI status every morning",
    )
    assert resolved is not None
    assert resolved.id == "automation.manage"


def test_resolver_respects_capability_gates(resolver: SkillResolver) -> None:
    """Ensure disabled capabilities prevent corresponding skills from resolving."""
    resolved = resolver.resolve(
        query="Research the latest docs on the web",
        available_capabilities={"developer_tools", "browser"},  # web_research excluded
    )
    # research.web should NOT be resolved when its capability gate is disabled
    if resolved:
        assert resolved.id != "research.web"


def test_resolver_disabled_skill_is_filtered(
    resolver: SkillResolver, registry_with_skills: SkillRegistry
) -> None:
    """Ensure skills explicitly disabled via registry cannot be resolved."""
    registry_with_skills.set_enabled("research.web", False)

    resolved = resolver.resolve(
        query="Search the web for python tutorials",
    )
    if resolved:
        assert resolved.id != "research.web"


def test_planner_creates_bounded_plan(
    planner: SkillPlanner, registry_with_skills: SkillRegistry
) -> None:
    """Ensure SkillPlanner constructs a structured, bounded plan under limit."""
    manifest = registry_with_skills.get("developer.repository")
    assert manifest is not None

    inputs = {"repository": "kairo", "branch": "main", "action": "status"}
    plan = planner.create_plan(manifest, inputs)
    assert plan is not None
    assert plan.skill_id == "developer.repository"
    assert len(plan.steps) > 0
    assert len(plan.steps) <= manifest.limits.max_steps
    assert all(step.tool_name in manifest.all_tools for step in plan.steps)


def test_planner_enforces_step_limit(
    planner: SkillPlanner, registry_with_skills: SkillRegistry
) -> None:
    """Ensure planner respects KAIRO_MAX_SKILL_STEPS and avoids infinite plans."""
    manifest = registry_with_skills.get("research.web")
    assert manifest is not None

    inputs = {"query": "quantum computing"}
    plan = planner.create_plan(manifest, inputs)
    assert len(plan.steps) <= 20  # KAIRO_MAX_SKILL_STEPS default
