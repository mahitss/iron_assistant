"""Simulation state modeling, copy-on-write branching, versioning, and diff tracking."""

from __future__ import annotations

import copy
import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from app.simulation.safety import tag_simulated_output


class StateDiff(BaseModel):
    """Detailed structural diff between two state dictionaries."""

    added: dict[str, Any] = Field(default_factory=dict)
    removed: dict[str, Any] = Field(default_factory=dict)
    modified: dict[str, dict[str, Any]] = Field(default_factory=dict)  # key -> {"before": val, "after": val}
    identical: bool = True


def calculate_state_diff(before: dict[str, Any], after: dict[str, Any]) -> StateDiff:
    """Computes recursive or top-level diff between before and after states."""
    added: dict[str, Any] = {}
    removed: dict[str, Any] = {}
    modified: dict[str, dict[str, Any]] = {}

    all_keys = set(before.keys()) | set(after.keys())
    for key in all_keys:
        if key not in before:
            added[key] = copy.deepcopy(after[key])
        elif key not in after:
            removed[key] = copy.deepcopy(before[key])
        elif before[key] != after[key]:
            modified[key] = {
                "before": copy.deepcopy(before[key]),
                "after": copy.deepcopy(after[key]),
            }

    identical = not (added or removed or modified)
    return StateDiff(
        added=added,
        removed=removed,
        modified=modified,
        identical=identical,
    )


class SimulationState(BaseModel):
    """Immutable simulated state frame."""

    state_id: str = Field(default_factory=lambda: f"state_{uuid.uuid4().hex[:12]}")
    version: int = 0
    base_snapshot_id: str
    data: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_hypothetical: bool = True
    environment_label: str = "SIMULATION_ONLY"


class SimulationStateManager:
    """Manages copy-on-write simulation state branching, transitions, and diffing."""

    def __init__(self) -> None:
        self._states: dict[str, SimulationState] = {}
        self._branches: dict[str, list[str]] = {}  # branch_id -> list of state_ids in order

    def initialize_branch(self, base_snapshot_id: str, initial_data: dict[str, Any]) -> str:
        """Initializes a new simulation branch from a snapshot baseline."""
        branch_id = f"branch_{uuid.uuid4().hex[:12]}"
        initial_clean = copy.deepcopy(initial_data)
        state = SimulationState(
            version=0,
            base_snapshot_id=base_snapshot_id,
            data=initial_clean,
        )
        self._states[state.state_id] = state
        self._branches[branch_id] = [state.state_id]
        return branch_id

    def apply_transition(
        self,
        branch_id: str,
        mutations: dict[str, Any],
    ) -> tuple[SimulationState, StateDiff]:
        """Applies mutations using copy-on-write, generating a new versioned state and diff."""
        if branch_id not in self._branches:
            raise KeyError(f"Simulation branch '{branch_id}' not found.")

        current_state_id = self._branches[branch_id][-1]
        parent_state = self._states[current_state_id]

        # Copy-on-write clone of parent data
        new_data = copy.deepcopy(parent_state.data)

        # Apply mutations deeply
        for k, v in mutations.items():
            if isinstance(v, dict) and isinstance(new_data.get(k), dict):
                new_data[k].update(v)
            else:
                new_data[k] = copy.deepcopy(v)

        # Compute state diff
        diff = calculate_state_diff(parent_state.data, new_data)

        new_state = SimulationState(
            version=parent_state.version + 1,
            base_snapshot_id=parent_state.base_snapshot_id,
            data=new_data,
        )
        self._states[new_state.state_id] = new_state
        self._branches[branch_id].append(new_state.state_id)

        return new_state, diff

    def get_latest_state(self, branch_id: str) -> SimulationState:
        """Retrieves the latest state of a simulation branch."""
        if branch_id not in self._branches:
            raise KeyError(f"Simulation branch '{branch_id}' not found.")
        latest_id = self._branches[branch_id][-1]
        return self._states[latest_id]

    def export_future_state(self, branch_id: str) -> dict[str, Any]:
        """Exports the latest state clearly marked as hypothetical future state."""
        state = self.get_latest_state(branch_id)
        raw = {
            "state_id": state.state_id,
            "version": state.version,
            "base_snapshot_id": state.base_snapshot_id,
            "data": copy.deepcopy(state.data),
            "created_at": state.created_at.isoformat(),
        }
        return tag_simulated_output(raw)
