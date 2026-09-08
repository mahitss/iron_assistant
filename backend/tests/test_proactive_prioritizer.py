"""Tests for deterministic priority and actionability assignment in Proactive Intelligence."""


from app.proactive.prioritizer import InsightPrioritizer
from app.proactive.state import Actionability, InsightPriority, SourceType


def test_priority_critical_for_emergency_stop():
    """Emergency stop events must always be CRITICAL and ACTION_REQUIRED."""
    p, a = InsightPrioritizer.calculate(
        source_type=SourceType.SECURITY,
        category="security.emergency_stop",
        metadata={"scope": "global"},
    )
    assert p == InsightPriority.CRITICAL
    assert a == Actionability.ACTION_REQUIRED


def test_priority_critical_cannot_be_set_by_llm():
    """An LLM suggestion of CRITICAL must be ignored and down-ranked or managed by rule."""
    p, a = InsightPrioritizer.calculate(
        source_type="CUSTOM",
        category="custom_event",
        metadata={},
        llm_suggested_priority="CRITICAL",
    )
    # LLM cannot assign CRITICAL!
    assert p != InsightPriority.CRITICAL


def test_priority_high_for_approval_and_workflow_failure():
    """Approvals and workflow failures receive HIGH priority."""
    p1, a1 = InsightPrioritizer.calculate(
        source_type=SourceType.APPROVAL,
        category="approval.required",
    )
    assert p1 == InsightPriority.HIGH
    assert a1 == Actionability.APPROVAL_REQUIRED

    p2, a2 = InsightPrioritizer.calculate(
        source_type=SourceType.WORKFLOW,
        category="workflow.failed",
        metadata={"status": "failed"},
    )
    assert p2 == InsightPriority.HIGH
    assert a2 == Actionability.ACTION_REQUIRED


def test_priority_branch_differentiation():
    """Main branch CI failure is HIGH, feature branch failure is MEDIUM."""
    p_main, _ = InsightPrioritizer.calculate(
        source_type=SourceType.GITHUB,
        category="github.ci.failed",
        metadata={"branch": "main", "conclusion": "failure"},
    )
    assert p_main == InsightPriority.HIGH

    p_feat, _ = InsightPrioritizer.calculate(
        source_type=SourceType.GITHUB,
        category="github.ci.failed",
        metadata={"branch": "feat/my-feature", "conclusion": "failure"},
    )
    assert p_feat == InsightPriority.MEDIUM


def test_priority_low_for_routine_workflow_completion():
    """Normal successful completions are classified as LOW / INFORMATIONAL."""
    p, a = InsightPrioritizer.calculate(
        source_type=SourceType.WORKFLOW,
        category="workflow.completed",
        metadata={"status": "completed"},
    )
    assert p == InsightPriority.LOW
    assert a == Actionability.INFORMATIONAL


def test_priority_threshold_comparison():
    """Validate threshold comparisons against minimum priority levels."""
    assert InsightPrioritizer.meets_priority_threshold("CRITICAL", "HIGH")
    assert InsightPrioritizer.meets_priority_threshold("HIGH", "HIGH")
    assert not InsightPrioritizer.meets_priority_threshold("MEDIUM", "HIGH")
    assert InsightPrioritizer.meets_priority_threshold("MEDIUM", "LOW")
    assert not InsightPrioritizer.meets_priority_threshold("LOW", "MEDIUM")
