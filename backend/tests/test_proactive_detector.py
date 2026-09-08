"""Tests for candidate event detection and filtering in Proactive Intelligence."""


from app.proactive.detector import ProactiveDetector
from app.proactive.state import Actionability, InsightPriority, SourceType


def test_detector_identifies_workflow_failure():
    """Workflow failures must be detected as candidate insights."""
    candidate = ProactiveDetector.create_candidate(
        user_id="user_1",
        source_type=SourceType.WORKFLOW,
        category="workflow.failed",
        payload={"workflow_name": "Daily Sync", "error": "Connection timed out"},
        source_id="wf_123",
    )
    assert candidate is not None
    assert candidate.user_id == "user_1"
    assert candidate.priority == InsightPriority.HIGH
    assert candidate.actionability == Actionability.ACTION_REQUIRED
    assert "Daily Sync" in candidate.title
    assert "Connection timed out" in candidate.summary
    assert candidate.suggested_action == "Investigate Workflow Run"


def test_detector_identifies_approval_required():
    """Pending approvals must be detected with APPROVAL_REQUIRED actionability."""
    candidate = ProactiveDetector.create_candidate(
        user_id="user_1",
        source_type=SourceType.APPROVAL,
        category="approval.required",
        payload={"tool_name": "github_push", "approval_id": "appr_999"},
        source_id="appr_999",
    )
    assert candidate is not None
    assert candidate.priority == InsightPriority.HIGH
    assert candidate.actionability == Actionability.APPROVAL_REQUIRED
    assert "Approval Waiting: github_push" in candidate.title


def test_detector_identifies_approval_expired():
    """Expired approvals must be detected."""
    candidate = ProactiveDetector.create_candidate(
        user_id="user_1",
        source_type=SourceType.APPROVAL,
        category="approval.expired",
        payload={"tool_name": "deploy_prod"},
        source_id="appr_888",
    )
    assert candidate is not None
    assert candidate.priority == InsightPriority.HIGH
    assert "Approval Expired" in candidate.title


def test_detector_identifies_ci_failure():
    """CI check failures on main branch must trigger high priority candidate."""
    candidate = ProactiveDetector.create_candidate(
        user_id="user_1",
        source_type=SourceType.GITHUB,
        category="github.ci.failed",
        payload={"repo": "kairo-core", "branch": "main", "stage": "pytest"},
    )
    assert candidate is not None
    assert candidate.priority == InsightPriority.HIGH
    assert candidate.actionability == Actionability.ACTION_REQUIRED
    assert "kairo-core" in candidate.title
    assert candidate.suggested_action == "View Run"


def test_detector_identifies_web_monitor_changed():
    """Web change detection events must produce candidates."""
    candidate = ProactiveDetector.create_candidate(
        user_id="user_1",
        source_type=SourceType.WEB_MONITOR,
        category="web_monitor.changed",
        payload={"monitor_name": "Python Docs", "url": "https://docs.python.org"},
    )
    assert candidate is not None
    assert candidate.priority == InsightPriority.MEDIUM
    assert candidate.actionability == Actionability.INFORMATIONAL
    assert "Python Docs" in candidate.title


def test_detector_ignores_routine_read_and_noise():
    """Routine read tools and noise must be rejected immediately."""
    assert not ProactiveDetector.is_candidate_event("TOOL", "tool_read", {"permission_level": "READ"})
    assert not ProactiveDetector.is_candidate_event("SYSTEM", "health_check", {})
    assert not ProactiveDetector.is_candidate_event("SYSTEM", "ping", {})
    assert not ProactiveDetector.is_candidate_event("MEMORY", "memory_retrieval", {})

    candidate = ProactiveDetector.create_candidate(
        user_id="user_1",
        source_type="TOOL",
        category="tool_read",
        payload={"permission_level": "READ"},
    )
    assert candidate is None
