"""Self-model snapshot generation, versioning, reconciliation, and anti-consciousness invariant enforcement (INVARIANTS 2, 3, 87-90, 155-157)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Dict, List, Optional
import uuid

from app.metacognition.capabilities import CapabilityManager
from app.metacognition.goals import GoalTracker
from app.metacognition.knowledge import KnowledgeStateTracker
from app.metacognition.limitations import LimitationDetector
from app.metacognition.policy_state import PolicyStateManager
from app.metacognition.resource_awareness import ResourceAwarenessTracker
from app.metacognition.safety import MetacognitiveSafetyGuard
from app.metacognition.schemas import SelfModelSchema
from app.metacognition.state import InternalStateManager
from app.metacognition.tasks import TaskTracker
from app.metacognition.uncertainty import UncertaintyModel


class SelfModelManager:
    """Orchestrates comprehensive operational snapshots representing system metadata only (INVARIANT 3: NEVER consciousness)."""

    def __init__(
        self,
        capability_manager: CapabilityManager,
        limitation_detector: LimitationDetector,
        knowledge_tracker: KnowledgeStateTracker,
        uncertainty_model: UncertaintyModel,
        goal_tracker: GoalTracker,
        task_tracker: TaskTracker,
        state_manager: InternalStateManager,
        resource_tracker: ResourceAwarenessTracker,
        policy_manager: PolicyStateManager,
        safety_guard: MetacognitiveSafetyGuard,
    ) -> None:
        self.capabilities = capability_manager
        self.limitations = limitation_detector
        self.knowledge = knowledge_tracker
        self.uncertainty = uncertainty_model
        self.goals = goal_tracker
        self.tasks = task_tracker
        self.state = state_manager
        self.resources = resource_tracker
        self.policy = policy_manager
        self.safety = safety_guard

        self.current_version: str = "1.0.0"
        self._snapshots: List[SelfModelSchema] = []

    def build_snapshot(self, user_id: str = "default_user") -> SelfModelSchema:
        """INVARIANT 2 & 87: Generates complete timestamped operational self-model snapshot."""
        model_id = str(uuid.uuid4())
        caps = {c.name: c for c in self.capabilities.list_capabilities()}
        limits = self.limitations.list_active_limitations()
        active_goals = self.goals.list_active_goals(user_id=user_id)
        active_tasks = self.tasks.list_active_tasks(user_id=user_id)

        snapshot = SelfModelSchema(
            model_id=model_id,
            version=self.current_version,
            capabilities=caps,
            limitations=limits,
            active_goals=active_goals,
            active_tasks=active_tasks,
            current_state=self.state.get_state(),
            knowledge_summary=self.knowledge.get_summary(),
            uncertainty_count=len(self.uncertainty.get_uncertainties()),
            resource_state=self.resources.get_state(),
            policy_state=self.policy.get_policy_summary(),
            authorization_state={"user_id": user_id, "mode": "STRICT_POLICY_ENFORCED"},
            is_operational_metadata_only=True,
            timestamp=datetime.now(UTC),
        )

        self._snapshots.append(snapshot)
        return snapshot

    def reconcile_self_model(self, registered_tools: List[str]) -> Dict[str, Any]:
        """INVARIANTS 155-157: Periodically reconciles self-model against ToolRegistry to detect capability drift."""
        self.capabilities.reconcile_with_tool_registry(registered_tools)
        return {
            "status": "RECONCILED",
            "capabilities_verified": len(self.capabilities.list_capabilities()),
            "timestamp": datetime.now(UTC).isoformat(),
        }

    def bump_version(self, major: bool = False) -> str:
        """INVARIANT 90: Versions important self-model changes."""
        parts = [int(p) for p in self.current_version.split(".")]
        if major:
            parts[0] += 1
            parts[1] = 0
            parts[2] = 0
        else:
            parts[1] += 1
            parts[2] = 0
        self.current_version = ".".join(str(p) for p in parts)
        return self.current_version
