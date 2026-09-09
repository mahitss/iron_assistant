"""Autonomous Execution State Machine, Autonomy Levels, and Action Taxonomies (Task 45)."""

from __future__ import annotations

from enum import Enum
import logging
from typing import Set

logger = logging.getLogger("kairo.autonomy.state")


class AutonomousRunState(str, Enum):
    """14 authoritative lifecycle states for long-horizon autonomous runs (Spec 3)."""

    CREATED = "CREATED"
    QUEUED = "QUEUED"
    INITIALIZING = "INITIALIZING"
    RUNNING = "RUNNING"
    WAITING = "WAITING"
    PAUSED = "PAUSED"
    REPLANNING = "REPLANNING"
    BLOCKED = "BLOCKED"
    RECOVERING = "RECOVERING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"
    SUPERSEDED = "SUPERSEDED"


class AutonomyLevel(str, Enum):
    """Configurable levels of agency bounding automated decision-making (Spec 134-138)."""

    ASSISTED = "ASSISTED"          # User confirms all significant consequential actions
    SUPERVISED = "SUPERVISED"      # System executes approved plan, pauses at configured checkpoints
    CONDITIONAL = "CONDITIONAL"    # Pre-authorized actions execute within explicit conditions
    AUTONOMOUS = "AUTONOMOUS"      # Full autonomy within policy, security, and contract bounds


class ActionClassification(str, Enum):
    """Taxonomy of consequential actions governed by autonomy policies (Spec 141, 142)."""

    READ = "READ"                  # Low-risk information retrieval
    ANALYZE = "ANALYZE"            # In-memory reasoning, evaluation, and synthesis
    WRITE = "WRITE"                # File modification, state mutation
    COMMUNICATE = "COMMUNICATE"    # Messaging peers, notifying users
    PUBLISH = "PUBLISH"            # External or public artifact distribution
    DEPLOY = "DEPLOY"              # Service deployment or environment modification
    DELETE = "DELETE"              # Destructive removal of resources
    PRIVILEGED = "PRIVILEGED"      # Administrative or security policy actions


# Legal transition graph for autonomous runs
VALID_STATE_TRANSITIONS: dict[AutonomousRunState, Set[AutonomousRunState]] = {
    AutonomousRunState.CREATED: {AutonomousRunState.QUEUED, AutonomousRunState.INITIALIZING, AutonomousRunState.CANCELLED},
    AutonomousRunState.QUEUED: {AutonomousRunState.INITIALIZING, AutonomousRunState.CANCELLED},
    AutonomousRunState.INITIALIZING: {AutonomousRunState.RUNNING, AutonomousRunState.BLOCKED, AutonomousRunState.FAILED, AutonomousRunState.CANCELLED},
    AutonomousRunState.RUNNING: {
        AutonomousRunState.WAITING,
        AutonomousRunState.PAUSED,
        AutonomousRunState.REPLANNING,
        AutonomousRunState.BLOCKED,
        AutonomousRunState.RECOVERING,
        AutonomousRunState.COMPLETED,
        AutonomousRunState.FAILED,
        AutonomousRunState.CANCELLED,
        AutonomousRunState.EXPIRED,
    },
    AutonomousRunState.WAITING: {
        AutonomousRunState.RUNNING,
        AutonomousRunState.PAUSED,
        AutonomousRunState.BLOCKED,
        AutonomousRunState.CANCELLED,
        AutonomousRunState.EXPIRED,
    },
    AutonomousRunState.PAUSED: {AutonomousRunState.RUNNING, AutonomousRunState.REPLANNING, AutonomousRunState.CANCELLED},
    AutonomousRunState.REPLANNING: {AutonomousRunState.RUNNING, AutonomousRunState.BLOCKED, AutonomousRunState.FAILED, AutonomousRunState.CANCELLED, AutonomousRunState.SUPERSEDED},
    AutonomousRunState.BLOCKED: {AutonomousRunState.REPLANNING, AutonomousRunState.PAUSED, AutonomousRunState.FAILED, AutonomousRunState.CANCELLED},
    AutonomousRunState.RECOVERING: {AutonomousRunState.RUNNING, AutonomousRunState.REPLANNING, AutonomousRunState.FAILED, AutonomousRunState.CANCELLED},
    AutonomousRunState.COMPLETED: set(),
    AutonomousRunState.FAILED: {AutonomousRunState.RECOVERING},  # Allowed if recovery engine reopens run
    AutonomousRunState.CANCELLED: set(),
    AutonomousRunState.EXPIRED: set(),
    AutonomousRunState.SUPERSEDED: set(),
}


def can_transition(current: AutonomousRunState, target: AutonomousRunState) -> bool:
    """Validate whether an autonomous run state transition is legal."""
    if current == target:
        return True
    return target in VALID_STATE_TRANSITIONS.get(current, set())
