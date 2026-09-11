"""Test suite for Cognitive Resource Allocation, EVOA, VOI, and Agent Delegation (Task 70)."""

from app.attention.delegation import AttentionDelegationEngine
from app.attention.resources import CognitiveResourceManager
from app.attention.schemas import AttentionCandidate, AttentionState, CognitiveResourceBudget


def test_cognitive_resource_allocation_and_release():
    """Resource manager strictly allocates and releases bounded capacity."""
    initial_budget = CognitiveResourceBudget(
        reasoning_capacity_pct=100.0,
        active_tool_calls=0,
        max_tool_calls=5,
        active_agent_slots=0,
        max_agent_slots=3,
        context_token_budget=10000,
        context_tokens_used=0,
    )
    mgr = CognitiveResourceManager(initial_budget)

    # 1. Allocate successfully for a task requiring 2 tool calls and an agent
    can, _ = mgr.can_allocate(
        estimated_effort=1.5, estimated_tool_calls=2, requires_agent=True, estimated_tokens=2000
    )
    assert can is True

    allocated = mgr.allocate(
        estimated_effort=1.5, estimated_tool_calls=2, requires_agent=True, estimated_tokens=2000
    )
    assert allocated is True
    assert mgr.budget.active_tool_calls == 2
    assert mgr.budget.active_agent_slots == 1
    assert mgr.budget.context_tokens_used == 2000
    assert mgr.budget.reasoning_capacity_pct < 100.0

    # 2. Exceeding tool quota must be rejected
    can_exceed, reason = mgr.can_allocate(estimated_tool_calls=4)
    assert can_exceed is False
    assert "Tool call quota exceeded" in reason

    # 3. Release restored resources
    mgr.release(estimated_effort=1.5, estimated_tool_calls=2, requires_agent=True, estimated_tokens=2000)
    assert mgr.budget.active_tool_calls == 0
    assert mgr.budget.active_agent_slots == 0
    assert mgr.budget.context_tokens_used == 0
    assert mgr.budget.reasoning_capacity_pct == 100.0


def test_evoa_and_voi_computation():
    """Test Expected Value of Attention (EVOA) and Value of Information (VOI)."""
    # High benefit, low effort task -> HIGH_VALUE EVOA
    net_evoa, tier, breakdown = CognitiveResourceManager.compute_evoa(
        importance=0.9,
        risk_reduction=0.85,
        goal_progress=0.8,
        user_value=0.8,
        estimated_effort=1.0,
    )
    assert net_evoa > 0.6
    assert tier == "HIGH_VALUE"
    assert breakdown["net_evoa"] == net_evoa

    # High uncertainty on high-consequence decision -> VOI justifies investigation
    net_voi, justified, voi_breakdown = CognitiveResourceManager.compute_voi(
        uncertainty=0.85,
        decision_consequence=0.90,
        investigation_cost=0.15,
    )
    assert justified is True
    assert net_voi > 0.5
    assert "Investigation justified" in voi_breakdown["explanation"]

    # Low consequence, high cost -> VOI does not justify investigation
    net_voi_low, justified_low, voi_breakdown_low = CognitiveResourceManager.compute_voi(
        uncertainty=0.20,
        decision_consequence=0.10,
        investigation_cost=0.30,
    )
    assert justified_low is False
    assert "Investigation not justified" in voi_breakdown_low["explanation"]


def test_agent_selection_competition():
    """Agent delegation evaluates capability matching and load rather than picking first agent."""
    cand = AttentionCandidate(
        title="Complex Incident Investigation",
        required_capabilities=["incident_triage", "database"],
        current_state=AttentionState.OBSERVED,
    )

    agents = [
        {"agent_id": "general-bot-1", "capabilities": ["general"], "load": 0.1, "success_rate": 0.7},
        {"agent_id": "sec-bot-1", "capabilities": ["incident_triage"], "load": 0.3, "success_rate": 0.9},
        {
            "agent_id": "db-sec-bot-1",
            "capabilities": ["incident_triage", "database"],
            "load": 0.2,
            "success_rate": 0.95,
        },
    ]

    selected_id, reason = AttentionDelegationEngine.select_best_agent(candidate=cand, available_agents=agents)
    assert selected_id == "db-sec-bot-1"
    assert "db-sec-bot-1" in reason


def test_agent_delegation_handoff_and_reclaim():
    """Delegation maintains history, allows safe handoff between agents, and orchestrator reclaim."""
    cand = AttentionCandidate(
        title="Root Cause Analysis",
        current_state=AttentionState.ATTENDING,
    )

    # 1. Delegate to Agent 1
    AttentionDelegationEngine.delegate(
        candidate=cand,
        target_agent_id="agent-alpha",
        reason="Assigned specialist investigation",
    )
    assert cand.current_state == AttentionState.DELEGATED
    assert cand.delegated_to == "agent-alpha"
    assert len(cand.delegation_history) == 1

    # 2. Agent 1 becomes unavailable -> Hand off to Agent 2
    AttentionDelegationEngine.handoff(
        candidate=cand,
        from_agent_id="agent-alpha",
        to_agent_id="agent-beta",
        reason="Agent alpha went offline; transferring context",
        interim_findings={"preliminary_culprit": "connection_leak"},
    )
    assert cand.delegated_to == "agent-beta"
    assert len(cand.delegation_history) == 2
    assert cand.delegation_history[-1]["interim_findings"]["preliminary_culprit"] == "connection_leak"

    # 3. Reclaim back to orchestrator
    AttentionDelegationEngine.reclaim(
        candidate=cand,
        reason="Incident completed; reclaiming oversight",
    )
    assert cand.current_state == AttentionState.ATTENDING
    assert cand.delegated_to is None
    assert len(cand.delegation_history) == 3
