"""Task Delegation, Primary Ownership, Spawn Limits, and Recursion Protection (Task 44)."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Optional

from app.agents.contracts import AgentContract

logger = logging.getLogger("kairo.agents.delegation")


def utc_now() -> datetime:
    return datetime.now(UTC)


class DelegationError(Exception):
    """Raised when delegation fails safety, depth, or concurrency bounds."""


class DelegationLoopError(DelegationError):
    """Raised when an illegal delegation cycle (A -> B -> A) is detected."""


class SpawnLimitExceededError(DelegationError):
    """Raised when concurrent agent spawn limits or max tree depth are exceeded."""


class OwnershipCollisionError(DelegationError):
    """Raised when attempting to assign a task that already has a primary owner."""


@dataclass
class DelegationNode:
    """A node in the collaborative delegation tree (Spec 95)."""

    delegation_id: str
    task_id: str
    objective: str
    owner_agent_id: str  # Spec 19: Exactly one primary owner per delegated task
    parent_delegation_id: str | None = None
    depth: int = 1
    child_delegation_ids: list[str] = field(default_factory=list)
    contract_id: str | None = None
    status: str = "PENDING"  # PENDING, RUNNING, COMPLETED, FAILED, CANCELLED
    role: str = ""
    created_at: datetime = field(default_factory=utc_now)


class DelegationTree:
    """Represents a hierarchical tree of delegated subtasks."""

    def __init__(self, root_id: str):
        self.root_id = root_id
        self.nodes: dict[str, DelegationNode] = {}

    def add_node(self, node: DelegationNode) -> None:
        self.nodes[node.delegation_id] = node


class DelegationManager:
    """Manages hierarchical subtask delegations with backpressure and loop safety (Spec 15, 93-98)."""

    def __init__(
        self,
        max_concurrent_agents: int = 10,
        max_tree_depth: int = 4,
        max_depth: Optional[int] = None,
    ) -> None:
        self.max_concurrent_agents = max_concurrent_agents
        self.max_tree_depth = max_depth if max_depth is not None else max_tree_depth
        self._nodes: dict[str, DelegationNode] = {}  # delegation_id -> node
        self._task_ownership: dict[str, str] = {}    # task_id -> primary_owner_agent_id
        self._parent_to_session: dict[str, str] = {}

    def delegate_subtask(
        self,
        task_id: str,
        objective: str,
        owner_agent_id: str,
        parent_delegation_id: str | None = None,
        contract: AgentContract | None = None,
        contract_id: str | None = None,
        role: str = "",
    ) -> DelegationNode:
        """Assign subtask to an authorized specialist primary owner (Spec 15, 19)."""
        # 1. Backpressure: Check max concurrent agents (Spec 93, 94)
        active_count = sum(1 for n in self._nodes.values() if n.status in ["PENDING", "RUNNING"])
        if active_count >= self.max_concurrent_agents:
            raise SpawnLimitExceededError(
                f"Backpressure: Active agent limit ({self.max_concurrent_agents}) reached. Cannot spawn new agent."
            )

        # 2. Check depth and loop detection (Spec 96, 97, 98)
        depth = 1
        parent_node: Optional[DelegationNode] = None
        if parent_delegation_id:
            if parent_delegation_id in self._nodes:
                parent_node = self._nodes[parent_delegation_id]
            else:
                for n in self._nodes.values():
                    if n.task_id == parent_delegation_id or n.owner_agent_id == parent_delegation_id:
                        parent_node = n
                        break

        if parent_node:
            depth = parent_node.depth + 1
            if depth > self.max_tree_depth:
                raise DelegationError(
                    f"Delegation recursion limit exceeded: depth {depth} exceeds max {self.max_tree_depth}."
                )

            # Detect delegation loop (Spec 97: A delegates to B, B delegates to A)
            curr_anc: Optional[DelegationNode] = parent_node
            visited_ancs: set[str] = set()
            while curr_anc and curr_anc.delegation_id not in visited_ancs:
                visited_ancs.add(curr_anc.delegation_id)
                if curr_anc.owner_agent_id == owner_agent_id:
                    raise DelegationLoopError(
                        f"Delegation loop detected: Agent '{owner_agent_id}' is already an ancestor in the delegation chain."
                    )
                # Walk up
                p_id = curr_anc.parent_delegation_id
                if p_id and p_id in self._nodes:
                    curr_anc = self._nodes[p_id]
                elif p_id:
                    curr_anc = next((n for n in self._nodes.values() if n.task_id == p_id or n.owner_agent_id == p_id), None)
                else:
                    curr_anc = None


        # 3. Enforce single primary task ownership (Spec 19)
        if task_id in self._task_ownership:
            existing_owner = self._task_ownership[task_id]
            if existing_owner != owner_agent_id:
                raise OwnershipCollisionError(
                    f"Task '{task_id}' already has primary owner '{existing_owner}'. Multi-ownership is disallowed."
                )
        self._task_ownership[task_id] = owner_agent_id

        # 4. Create Node
        node_id = f"del_{uuid.uuid4().hex[:10]}"
        cid = contract_id or (contract.contract_id if contract else None)
        node = DelegationNode(
            delegation_id=node_id,
            task_id=task_id,
            objective=objective,
            owner_agent_id=owner_agent_id,
            parent_delegation_id=parent_delegation_id,
            depth=depth,
            contract_id=cid,
            status="PENDING",
            role=role,
        )
        self._nodes[node_id] = node

        if parent_delegation_id and parent_delegation_id in self._nodes:
            self._nodes[parent_delegation_id].child_delegation_ids.append(node_id)

        logger.info(
            "Delegated task '%s' (depth %d) to primary owner '%s'",
            task_id,
            depth,
            owner_agent_id,
        )
        return node

    def delegate(
        self,
        parent_task_id: str,
        subtask_id: str,
        objective: str,
        agent_id: str,
        contract_id: str | None = None,
        role: str = "",
    ) -> DelegationNode:
        """Alias for delegate_subtask."""
        return self.delegate_subtask(
            task_id=subtask_id,
            objective=objective,
            owner_agent_id=agent_id,
            parent_delegation_id=parent_task_id,
            contract_id=contract_id,
            role=role,
        )

    def get_task_owner(self, task_id: str) -> str | None:
        """Get the single authoritative primary owner of a task."""
        return self._task_ownership.get(task_id)

    def get_subtask_owner(self, subtask_id: str) -> str | None:
        """Alias for get_task_owner."""
        return self.get_task_owner(subtask_id)

    def update_status(self, delegation_id: str, new_status: str) -> None:
        if delegation_id in self._nodes:
            self._nodes[delegation_id].status = new_status

    def cancel_session(self, session_id: str) -> int:
        """Halt/cancel all delegations associated with a session."""
        cancelled = 0
        for n in self._nodes.values():
            if n.status in ["PENDING", "RUNNING"]:
                n.status = "CANCELLED"
                cancelled += 1
        return cancelled

    def get_delegation_tree(self) -> list[dict[str, Any]]:
        return [
            {
                "delegation_id": n.delegation_id,
                "task_id": n.task_id,
                "objective": n.objective,
                "owner_agent_id": n.owner_agent_id,
                "parent_delegation_id": n.parent_delegation_id,
                "depth": n.depth,
                "child_delegation_ids": n.child_delegation_ids,
                "contract_id": n.contract_id,
                "status": n.status,
                "created_at": n.created_at.isoformat(),
            }
            for n in self._nodes.values()
        ]
