"""Enterprise Agent domain model and specialist role taxonomy (Task 44)."""

from __future__ import annotations

import enum
import uuid
from datetime import UTC, datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


def utc_now() -> datetime:
    return datetime.now(UTC)


class AgentRole(str, enum.Enum):
    """Specialist capability roles for collaborative execution (Spec 3).
    
    CRITICAL: Roles are capability labels only. A role does NOT grant authorization.
    Authorization is always external, enforced by PolicyEngine and SecurityCenter (Spec 5).
    """

    SUPERVISOR = "SUPERVISOR"
    RESEARCHER = "RESEARCHER"
    CODER = "CODER"
    ANALYST = "ANALYST"
    PLANNER = "PLANNER"
    DEBUGGER = "DEBUGGER"
    REVIEWER = "REVIEWER"
    SECURITY_ANALYST = "SECURITY_ANALYST"
    DATA_ANALYST = "DATA_ANALYST"
    VISION_ANALYST = "VISION_ANALYST"
    WRITER = "WRITER"
    TESTER = "TESTER"
    VERIFIER = "VERIFIER"
    BROWSER_OPERATOR = "BROWSER_OPERATOR"
    SYSTEM_OPERATOR = "SYSTEM_OPERATOR"


class AgentStatus(str, enum.Enum):
    """Lifecycle status of an individual agent instance (Spec 9)."""

    CREATED = "CREATED"
    READY = "READY"
    RUNNING = "RUNNING"
    WAITING = "WAITING"
    DRAINING = "DRAINING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    TERMINATED = "TERMINATED"


class Agent(BaseModel):
    """Collaborative specialist agent instance governed under contract (Spec 2)."""

    model_config = ConfigDict(extra="ignore", arbitrary_types_allowed=True)

    agent_id: str = Field(default_factory=lambda: f"ag_{uuid.uuid4().hex[:10]}")
    name: str = Field(..., description="Human-readable specialist name")
    role: AgentRole = Field(..., description="Specialist capability role")
    capabilities: list[str] = Field(default_factory=list, description="Reasoning and task capabilities")
    status: AgentStatus = Field(default=AgentStatus.CREATED)
    version: str = Field(default="1.0.0")
    model_profile: str = Field(default="default", description="Model profile hint for ModelRouter")
    permissions_scope: list[str] = Field(default_factory=list, description="Explicit permitted action scopes")
    tool_scope: list[str] = Field(default_factory=list, description="Authorized tool categories or names")
    resource_budget: Any = Field(default_factory=lambda: {
        "max_tokens": 100000,
        "max_tool_calls": 20,
        "max_duration_seconds": 300,
        "max_cost_usd": 0.50,
    })
    trust_metadata: dict[str, Any] = Field(default_factory=lambda: {
        "is_quarantined": False,
        "reputation_score": 1.0,
        "verified_tasks_count": 0,
    })
    health: str = Field(default="HEALTHY", description="HEALTHY, DEGRADED, UNAVAILABLE, FAILED, DRAINING")
    is_experimental: bool = False
    created_at: datetime = Field(default_factory=utc_now)

    def can_handle_capability(self, capability: str) -> bool:
        """Check if agent possesses reasoning capability."""
        return capability.lower() in [c.lower() for c in self.capabilities]

    def is_tool_in_scope(self, tool_name: str) -> bool:
        """Check whether requested tool is within defined contract tool scope (Spec 71)."""
        clean = tool_name.strip().lower()
        return any(clean == s.lower() or s == "*" for s in self.tool_scope)

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "role": self.role.value if hasattr(self.role, "value") else str(self.role),
            "capabilities": self.capabilities,
            "status": self.status.value if hasattr(self.status, "value") else str(self.status),
            "version": self.version,
            "model_profile": self.model_profile,
            "permissions_scope": self.permissions_scope,
            "tool_scope": self.tool_scope,
            "resource_budget": self.resource_budget,
            "trust_metadata": self.trust_metadata,
            "health": self.health,
            "is_experimental": self.is_experimental,
            "created_at": self.created_at.isoformat(),
        }
