"""Unit tests for Swarm Agents, Registry, Health Tracking, and Agent Selection (Task 64)."""

from app.swarm.agents import SwarmAgentRegistry
from app.swarm.schemas import (
    AgentHealthState,
    CollectiveObjective,
    SwarmAgentSpec,
)
from app.swarm.selection import AgentSelector


def test_swarm_agent_registry_initialization_and_defaults():
    registry = SwarmAgentRegistry()
    agents = registry.list_agents()

    assert len(agents) >= 10
    roles = {a.role for a in agents}
    assert "ARCHITECT" in roles
    assert "SECURITY_ANALYST" in roles
    assert "CRITIC" in roles
    assert "FACT_CHECKER" in roles
    assert "SYNTHESIZER" in roles
    assert "FORECASTER" in roles
    assert "OPTIMIZER" in roles


def test_swarm_agent_capability_versus_authorization():
    registry = SwarmAgentRegistry()
    sec_agent = registry.get_agent("ag_security_analyst")
    assert sec_agent is not None

    # Capabilities must be declared
    assert "threat_modeling" in sec_agent.capabilities
    assert "vulnerability_audit" in sec_agent.capabilities

    # Capabilities do NOT imply production modification authorization
    assert "modify_production_security_config" not in sec_agent.permissions
    assert sec_agent.can_execute_production is False
    assert any("cannot modify authorization policies" in lim.lower() for lim in sec_agent.limitations)


def test_swarm_agent_health_state_transitions():
    registry = SwarmAgentRegistry()
    agent_id = "ag_architect"

    # Default is HEALTHY
    agent = registry.get_agent(agent_id)
    assert agent is not None
    assert agent.health == AgentHealthState.HEALTHY

    # Transition to DEGRADED
    updated = registry.update_health(agent_id, AgentHealthState.DEGRADED)
    assert updated.health == AgentHealthState.DEGRADED

    # Unknown health must NOT be treated as healthy
    unknown_agt = SwarmAgentSpec(
        agent_id="test_unknown_01",
        name="Test Unknown Agent",
        role="ANALYST",
        description="Testing unknown state",
        capabilities=["data_analysis"],
        limitations=["unverified"],
        health=AgentHealthState.UNKNOWN,
    )
    assert unknown_agt.health == AgentHealthState.UNKNOWN
    assert unknown_agt.health != AgentHealthState.HEALTHY


def test_swarm_agent_registration_and_disable():
    registry = SwarmAgentRegistry()
    custom_agent = SwarmAgentSpec(
        agent_id="swm_agt_custom_perf_01",
        name="Performance Optimizer Agent",
        role="OPTIMIZER",
        description="Profile memory and latency",
        capabilities=["profiling", "latency_reduction"],
        limitations=["no production rollout"],
        model="gemini-1.5-pro",
    )
    registry.register(custom_agent)
    assert registry.get_agent("swm_agt_custom_perf_01") is not None

    # Disable agent
    disabled = registry.disable_agent("swm_agt_custom_perf_01")
    assert disabled.health == AgentHealthState.DISABLED

    # Available agents should not include disabled
    available = registry.list_available()
    assert all(a.agent_id != "swm_agt_custom_perf_01" for a in available)


def test_swarm_agent_selector_diversity_and_multi_perspective():
    registry = SwarmAgentRegistry()
    selector = AgentSelector(registry)

    objective = CollectiveObjective(
        goal="Evaluate zero-downtime database migration for high-throughput tenant",
        context={"db_type": "postgres", "throughput_qps": 50000},
        risk_level="HIGH",
        priority="HIGH",
    )

    selected = selector.select_diverse_team(objective, min_perspectives=4)

    assert len(selected) >= 4
    roles = [a.role for a in selected]

    # Must contain specialized multi-perspectives for high-risk problem
    assert "ARCHITECT" in roles or "STRATEGIST" in roles
    assert "SECURITY_ANALYST" in roles or "RISK_ANALYST" in roles
    assert "CRITIC" in roles  # Red-team / adversarial perspective
    assert "SYNTHESIZER" in roles or "FACT_CHECKER" in roles


def test_swarm_agent_selector_excludes_degraded_and_disabled():
    registry = SwarmAgentRegistry()
    # Degrade security agent
    registry.update_health("ag_security_analyst", AgentHealthState.DEGRADED)

    selector = AgentSelector(registry)
    objective = CollectiveObjective(
        goal="Routine software refactoring task",
        risk_level="LOW",
        priority="LOW",
    )

    healthy_pool = selector.get_eligible_agents(objective)
    assert all(a.agent_id != "ag_security_analyst" for a in healthy_pool)
