"""Unit tests for failure classification, transparent causality, error memory, and structured reflection."""

from datetime import UTC, datetime, timedelta

from app.metacognition.errors import ErrorMemoryManager
from app.metacognition.failures import FailureClassifier
from app.metacognition.reflection import ReflectionEngine
from app.metacognition.schemas import FailureCertainty, FailureType


def test_failure_classification_and_transparent_causality():
    classifier = FailureClassifier(default_max_retries=3)

    # Invariant 53 & 54: Do not invent causes; if cause is unknown, explicitly mark UNCERTAIN
    fail_unc = classifier.record_failure(
        action="execute_sandbox_script",
        failure_type=FailureType.TOOL_FAILURE,
        cause=None,  # No cause provided
        task_id="task_100",
    )

    assert fail_unc.certainty == FailureCertainty.UNKNOWN
    assert "UNCERTAIN" in fail_unc.cause

    # Explicit failure with known root cause
    fail_known = classifier.record_failure(
        action="connect_remote_host",
        failure_type=FailureType.NETWORK_FAILURE,
        cause="Connection timed out after 30000ms",
        task_id="task_101",
        certainty=FailureCertainty.KNOWN,
    )
    assert fail_known.certainty == FailureCertainty.KNOWN
    assert "Connection timed out" in fail_known.cause


def test_failure_retry_bounds_and_safety():
    classifier = FailureClassifier(default_max_retries=2)

    # Policy block and Auth failures must NEVER be retried automatically
    fail_auth = classifier.record_failure(
        action="delete_database_cluster",
        failure_type=FailureType.POLICY_BLOCK,
        cause="Operation prohibited by enterprise safety policy",
    )
    assert classifier.can_retry(fail_auth.failure_id) is False

    # Tool failure can be retried up to limit
    fail_tool = classifier.record_failure(
        action="query_github_api",
        failure_type=FailureType.TOOL_FAILURE,
        cause="Rate limit secondary throttle",
        recoverability="RECOVERABLE",
    )
    assert classifier.can_retry(fail_tool.failure_id) is True
    assert classifier.increment_retry(fail_tool.failure_id) == 1
    assert classifier.increment_retry(fail_tool.failure_id) == 2
    # Invariant 57: Respect retry budget, no infinite retry
    assert classifier.can_retry(fail_tool.failure_id) is False


def test_error_memory_decay_and_pattern_escalation():
    error_mgr = ErrorMemoryManager(decay_hours=1)

    # Record errors
    error_mgr.record_error("web_research", "HTTP 502 Bad Gateway", is_transient=True)
    error_mgr.record_error("web_research", "HTTP 504 Gateway Timeout", is_transient=True)

    # Initial pattern check (threshold 3)
    pattern1 = error_mgr.detect_failure_pattern("web_research", threshold=3)
    assert pattern1["is_repeated_pattern"] is False

    # Third error triggers pattern detection & escalation
    error_mgr.record_error("web_research", "HTTP 503 Service Unavailable", is_transient=True)
    pattern2 = error_mgr.detect_failure_pattern("web_research", threshold=3)
    assert pattern2["is_repeated_pattern"] is True
    assert pattern2["escalation_required"] is True

    # Mark recovered
    error_mgr.mark_recovered("web_research")
    pattern_recovered = error_mgr.detect_failure_pattern("web_research", threshold=3)
    assert pattern_recovered["is_repeated_pattern"] is False
    assert pattern_recovered["recent_failures_count"] == 0


def test_reflection_engine_and_evidence_grounded_lessons():
    engine = ReflectionEngine()

    # Invariants 62-65: 6 core questions, structured outcome, evidence-grounded lessons
    reflection = engine.conduct_reflection(
        goal="Extract data from internal dashboard",
        attempted="Direct headless browser scrape",
        worked=["Browser launched", "Target page loaded"],
        failed=["Auth cookie missing"],
        verified=["Page responded with 401"],
        remaining_uncertainties=["Session token TTL"],
        lessons=["Always verify active session before navigating protected dashboard"],
        corrections_applied=["Add token check precondition to browser tasks"],
        lesson_evidence={"source": "telemetry_run_991"},
    )

    assert reflection.goal == "Extract data from internal dashboard"
    assert "Evidence: telemetry_run_991" in reflection.lessons[0]
    assert len(reflection.corrections_applied) == 1

    # Invariants 66 & 67: Exported lessons preserve security/policy immutability
    lessons_exported = engine.export_lessons_for_learning()
    assert len(lessons_exported) == 1
    assert lessons_exported[0]["security_policy_immutable"] is True
