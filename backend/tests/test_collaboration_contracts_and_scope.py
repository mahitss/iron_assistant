"""Tests for Agent Contracts, Scope Boundaries, and Expansion Requests (Task 44)."""

import pytest
from app.agents.budgets import AgentBudget, BudgetExhaustedError
from app.agents.contracts import (
    AgentContract,
    ContractExpansionRequest,
    ContractScope,
    ContractStatus,
    ScopeViolationError,
)


def test_contract_creation_and_bounds():
    scope = ContractScope(
        resources=["repo/backend/app/auth/"],
        tools=["code_read_file", "code_search"],
        data=["auth_tokens"],
        project_id="proj_alpha",
    )
    budget = AgentBudget(max_tokens=5000, max_tool_calls=10, max_cost=0.25)
    contract = AgentContract(
        contract_id="ct_001",
        agent_id="agent_coder",
        parent_goal="Audit Authentication Module",
        assigned_objective="Scan JWT verification routines for algorithm confusion",
        scope=scope,
        budget=budget,
    )

    assert contract.contract_id == "ct_001"
    assert contract.status == ContractStatus.ACTIVE
    assert contract.is_in_scope(resource="repo/backend/app/auth/jwt.py") is True
    assert contract.is_in_scope(resource="repo/backend/app/billing/payments.py") is False
    assert contract.is_tool_allowed("code_read_file") is True
    assert contract.is_tool_allowed("git_push") is False


def test_no_silent_scope_expansion():
    """Agent cannot silently operate outside contract; must request expansion."""
    scope = ContractScope(
        resources=["docs/"],
        tools=["web_search"],
        project_id="proj_alpha",
    )
    contract = AgentContract(
        contract_id="ct_002",
        agent_id="agent_researcher",
        parent_goal="Research RFCs",
        assigned_objective="Gather OAuth2 RFC specs",
        scope=scope,
    )

    # Attempting to access unauthorized tool raises ScopeViolationError
    with pytest.raises(ScopeViolationError):
        contract.validate_tool_access("file_write")

    # Attempting to access unauthorized resource raises ScopeViolationError
    with pytest.raises(ScopeViolationError):
        contract.validate_resource_access("secret/keys.pem")


def test_contract_expansion_request_and_approval():
    scope = ContractScope(
        resources=["frontend/"],
        tools=["code_read_file"],
        project_id="proj_beta",
    )
    contract = AgentContract(
        contract_id="ct_003",
        agent_id="agent_tester",
        parent_goal="Test UI",
        assigned_objective="Run component test suite",
        scope=scope,
        budget=AgentBudget(max_tokens=1000, max_tool_calls=2),
    )

    expansion = ContractExpansionRequest(
        request_id="exp_01",
        contract_id="ct_003",
        reason="Need test runner tool and access to fixtures directory",
        requested_resources=["fixtures/"],
        requested_tools=["test_runner"],
        requested_token_budget=5000,
    )

    # Apply expansion
    approved = contract.apply_expansion(expansion)
    assert approved is True
    assert contract.is_tool_allowed("test_runner") is True
    assert contract.is_in_scope(resource="fixtures/mock_data.json") is True
    assert contract.budget.max_tokens == 5000


def test_contract_budget_exhaustion():
    budget = AgentBudget(max_tokens=100, max_tool_calls=2)
    contract = AgentContract(
        contract_id="ct_004",
        agent_id="agent_analyst",
        parent_goal="Analysis",
        assigned_objective="Analyze metrics",
        budget=budget,
    )

    contract.consume_budget(tokens=50, tool_calls=1, cost=0.01)
    assert contract.budget.used_tokens == 50
    assert contract.budget.used_tool_calls == 1

    # Consuming beyond limit raises BudgetExhaustedError
    with pytest.raises(BudgetExhaustedError):
        contract.consume_budget(tokens=60, tool_calls=1)
