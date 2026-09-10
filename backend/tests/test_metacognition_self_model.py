"""Unit tests for operational self-model snapshot generation, versioning, and reconciliation."""

from app.metacognition.capabilities import CapabilityManager
from app.metacognition.goals import GoalTracker
from app.metacognition.knowledge import KnowledgeStateTracker
from app.metacognition.limitations import LimitationDetector
from app.metacognition.policy_state import PolicyStateManager
from app.metacognition.resource_awareness import ResourceAwarenessTracker
from app.metacognition.safety import MetacognitiveSafetyGuard
from app.metacognition.self_model import SelfModelManager
from app.metacognition.state import InternalStateManager
from app.metacognition.tasks import TaskOrigin, TaskTracker
from app.metacognition.uncertainty import UncertaintyModel


def test_self_model_snapshot_generation():
    caps = CapabilityManager()
    limits = LimitationDetector()
    knowledge = KnowledgeStateTracker()
    uncertainty = UncertaintyModel()
    goals = GoalTracker()
    tasks = TaskTracker()
    state = InternalStateManager()
    resources = ResourceAwarenessTracker()
    policy = PolicyStateManager()
    safety = MetacognitiveSafetyGuard()

    manager = SelfModelManager(
        capability_manager=caps,
        limitation_detector=limits,
        knowledge_tracker=knowledge,
        uncertainty_model=uncertainty,
        goal_tracker=goals,
        task_tracker=tasks,
        state_manager=state,
        resource_tracker=resources,
        policy_manager=policy,
        safety_guard=safety,
    )

    # Register goal and task
    goals.register_goal("Build release bundle", user_id="user_1")
    tasks.register_task("compile_assets", TaskOrigin.USER, user_id="user_1")

    # Generate snapshot
    snapshot = manager.build_snapshot(user_id="user_1")

    assert snapshot.version == "1.0.0"
    assert snapshot.is_operational_metadata_only is True
    assert "text_generation" in snapshot.capabilities
    assert len(snapshot.active_goals) == 1
    assert len(snapshot.active_tasks) == 1
    assert snapshot.current_state == "IDLE"
    assert snapshot.timestamp is not None


def test_self_model_versioning_and_reconciliation():
    caps = CapabilityManager()
    limits = LimitationDetector()
    knowledge = KnowledgeStateTracker()
    uncertainty = UncertaintyModel()
    goals = GoalTracker()
    tasks = TaskTracker()
    state = InternalStateManager()
    resources = ResourceAwarenessTracker()
    policy = PolicyStateManager()
    safety = MetacognitiveSafetyGuard()

    manager = SelfModelManager(
        capability_manager=caps,
        limitation_detector=limits,
        knowledge_tracker=knowledge,
        uncertainty_model=uncertainty,
        goal_tracker=goals,
        task_tracker=tasks,
        state_manager=state,
        resource_tracker=resources,
        policy_manager=policy,
        safety_guard=safety,
    )

    # Minor version bump
    v1_1 = manager.bump_version(major=False)
    assert v1_1 == "1.1.0"

    # Major version bump
    v2_0 = manager.bump_version(major=True)
    assert v2_0 == "2.0.0"

    # Reconcile with registered tools
    recon = manager.reconcile_self_model(["web_search", "web_fetch", "calculator"])
    assert recon["status"] == "RECONCILED"
