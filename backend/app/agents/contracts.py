"""Agent Contracts, Scope Boundary Enforcement, and Expansion Protocols (Task 44)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
import enum
import logging
from typing import Any, Optional, Union
import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.agents.budgets import AgentBudget, BudgetExhaustedError

logger = logging.getLogger("kairo.agents.contracts")


def utc_now() -> datetime:
    return datetime.now(UTC)


class ContractStatus(str, enum.Enum):
    """Lifecycle status of an active agent contract."""

    ACTIVE = "ACTIVE"
    FULFILLED = "FULFILLED"
    EXPANSION_REQUESTED = "EXPANSION_REQUESTED"
    VIOLATED = "VIOLATED"
    CANCELLED = "CANCELLED"


class ScopeViolationError(Exception):
    """Raised when an agent attempts an action or resource access outside its contract scope."""


@dataclass
class ContractScope:
    """Explicit bounded scope for an agent contract (Spec 11, 12)."""

    resources: list[str] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)
    data: list[str] = field(default_factory=list)
    project_id: str = "default_project"
    environment: str = "sandbox"
    read_only: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "resources": self.resources,
            "tools": self.tools,
            "data": self.data,
            "project_id": self.project_id,
            "environment": self.environment,
            "read_only": self.read_only,
        }


class ContractExpansionRequest(BaseModel):
    """Formal request submitted by an agent when an unpredicted requirement is discovered (Spec 13, 14)."""

    model_config = ConfigDict(extra="ignore")

    request_id: str = Field(default_factory=lambda: f"exp_req_{uuid.uuid4().hex[:8]}")
    contract_id: str
    agent_id: str = ""
    reason: str = Field(default="", description="Justification for scope expansion")
    new_requirement: str = Field(default="", description="Alias for reason")
    requested_tools: list[str] = Field(default_factory=list)
    requested_resources: list[str] = Field(default_factory=list)
    requested_token_budget: Optional[int] = None
    requested_budget_extension: dict[str, Any] = Field(default_factory=dict)
    status: str = "PENDING"  # PENDING, APPROVED, REJECTED
    reviewed_by: Optional[str] = None
    created_at: datetime = Field(default_factory=utc_now)

    def __init__(self, **data: Any):
        if "reason" in data and not data.get("new_requirement"):
            data["new_requirement"] = data["reason"]
        elif "new_requirement" in data and not data.get("reason"):
            data["reason"] = data["new_requirement"]
        super().__init__(**data)


class AgentContract:
    """Authoritative execution boundary and SLA assigned to a specialist agent (Spec 10, 11)."""

    def __init__(
        self,
        contract_id: Optional[str] = None,
        agent_id: str = "",
        agent_role: str = "",
        parent_goal: str = "",
        assigned_objective: str = "",
        scope: Optional[Union[ContractScope, dict[str, Any]]] = None,
        budget: Optional[Union[AgentBudget, dict[str, Any]]] = None,
        status: ContractStatus = ContractStatus.ACTIVE,
        collaboration_id: Optional[str] = None,
        inputs: Optional[dict[str, Any]] = None,
        expected_outputs: Optional[dict[str, Any]] = None,
        constraints: Optional[list[str]] = None,
        success_criteria: Optional[list[str]] = None,
        verification_requirements: Optional[list[str]] = None,
        permissions: Optional[list[str]] = None,
        created_at: Optional[datetime] = None,
    ):
        self.contract_id = contract_id or f"ctr_{uuid.uuid4().hex[:10]}"
        self.agent_id = agent_id
        self.agent_role = agent_role
        self.parent_goal = parent_goal
        self.assigned_objective = assigned_objective
        self.status = status
        self.collaboration_id = collaboration_id
        self.inputs = inputs or {}
        self.expected_outputs = expected_outputs or {}
        self.constraints = constraints or []
        self.success_criteria = success_criteria or []
        self.verification_requirements = verification_requirements or []
        self.permissions = permissions or []
        self.expansion_requests: list[ContractExpansionRequest] = []
        self.created_at = created_at or utc_now()

        # Handle scope normalization
        if isinstance(scope, ContractScope):
            self.scope = scope
        elif isinstance(scope, dict):
            self.scope = ContractScope(
                resources=scope.get("resources") or scope.get("allowed_resources") or [],
                tools=scope.get("tools") or scope.get("allowed_tools") or [],
                data=scope.get("data") or [],
                project_id=scope.get("project_id", "default_project"),
                environment=scope.get("environment", "sandbox"),
                read_only=scope.get("read_only", True),
            )
        else:
            self.scope = ContractScope()

        # Handle budget normalization
        if isinstance(budget, AgentBudget):
            self.budget = budget
        elif isinstance(budget, dict):
            self.budget = AgentBudget(
                max_tokens=budget.get("max_tokens", 50000),
                max_tool_calls=budget.get("max_tool_calls", 20),
                max_cost=budget.get("max_cost_usd", budget.get("max_cost", 1.0)),
            )
        else:
            self.budget = AgentBudget()

    def is_in_scope(self, resource: str) -> bool:
        """Check whether a specific target resource is permitted by contract."""
        if not self.scope.resources:
            return False
        if "*" in self.scope.resources:
            return True
        for allowed in self.scope.resources:
            if resource == allowed or resource.startswith(allowed):
                return True
        return False

    def is_tool_allowed(self, tool_name: str) -> bool:
        """Check whether a tool call is authorized by contract."""
        if "*" in self.scope.tools:
            return True
        return tool_name in self.scope.tools

    def validate_tool_access(self, tool_name: str) -> None:
        """Validate tool access, raising ScopeViolationError if unauthorized."""
        if not self.is_tool_allowed(tool_name):
            raise ScopeViolationError(
                f"Agent {self.agent_id} is not authorized for tool '{tool_name}' under contract {self.contract_id}"
            )

    def validate_resource_access(self, resource: str) -> None:
        """Validate resource access, raising ScopeViolationError if unauthorized."""
        if not self.is_in_scope(resource):
            raise ScopeViolationError(
                f"Resource '{resource}' is outside scope of contract {self.contract_id} for agent {self.agent_id}"
            )

    def consume_budget(self, tokens: int = 0, tool_calls: int = 0, cost: float = 0.0) -> None:
        """Deduct resource consumption; raises BudgetExhaustedError if limits exceeded."""
        self.budget.consume(tokens=tokens, tool_calls=tool_calls, cost=cost)

    def request_scope_expansion(
        self,
        new_requirement: str = "",
        requested_tools: Optional[list[str]] = None,
        requested_resources: Optional[list[str]] = None,
        requested_budget_extension: Optional[dict[str, Any]] = None,
    ) -> ContractExpansionRequest:
        """Agent pauses execution and requests scope expansion from Supervisor (Spec 13, 14)."""
        req = ContractExpansionRequest(
            contract_id=self.contract_id,
            agent_id=self.agent_id,
            new_requirement=new_requirement,
            reason=new_requirement,
            requested_tools=requested_tools or [],
            requested_resources=requested_resources or [],
            requested_budget_extension=requested_budget_extension or {},
        )
        self.status = ContractStatus.EXPANSION_REQUESTED
        self.expansion_requests.append(req)
        logger.info("Agent '%s' requested contract expansion on '%s': %s", self.agent_id, self.contract_id, new_requirement)
        return req

    def apply_expansion(self, expansion_req: ContractExpansionRequest) -> bool:
        """Supervisor approves and applies expansion to contract."""
        expansion_req.status = "APPROVED"
        for t in expansion_req.requested_tools:
            if t not in self.scope.tools:
                self.scope.tools.append(t)
        for r in expansion_req.requested_resources:
            if r not in self.scope.resources:
                self.scope.resources.append(r)
        if expansion_req.requested_token_budget:
            self.budget.max_tokens = expansion_req.requested_token_budget

        self.status = ContractStatus.ACTIVE
        return True

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "collaboration_id": self.collaboration_id,
            "parent_goal": self.parent_goal,
            "assigned_objective": self.assigned_objective,
            "agent_id": self.agent_id,
            "agent_role": self.agent_role,
            "status": self.status.value,
            "scope": self.scope.to_dict(),
            "inputs": self.inputs,
            "expected_outputs": self.expected_outputs,
            "constraints": self.constraints,
            "budget": self.budget.to_dict(),
            "success_criteria": self.success_criteria,
            "verification_requirements": self.verification_requirements,
            "permissions": self.permissions,
            "created_at": self.created_at.isoformat(),
        }
