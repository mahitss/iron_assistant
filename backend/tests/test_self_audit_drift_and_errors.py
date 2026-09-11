"""Unit tests for Behavior Drift, Proxy Gaming, Error Taxonomy, and Rationalization (Task 67)."""

from app.self_audit.drift import BehaviorDriftDetector, GoalAlignmentAuditor
from app.self_audit.errors import ErrorManager, InterventionTracker, RationalizationDetector
from app.self_audit.schemas import ErrorCategory, ErrorSeverity


def test_behavior_drift_detection():
    detector = BehaviorDriftDetector()

    # Normal reading (no drift)
    b1 = detector.update_metric("verification_frequency", 0.88)
    assert b1.is_drifting is False

    # Significant drop (Spec 34): 0.90 -> 0.45 (50% drop, exceeds 30% threshold)
    b2 = detector.update_metric("verification_frequency", 0.45)
    assert b2.is_drifting is True
    assert "BEHAVIOR_DRIFT" in b2.drift_reason

    active = detector.get_active_drifts()
    assert len(active) >= 1
    assert active[0]["metric_name"] == "verification_frequency"


def test_goal_alignment_and_proxy_gaming():
    # Goal Alignment (Spec 35)
    aligned = GoalAlignmentAuditor.audit_goal_alignment(
        original_goal_description="Reduce API latency under high concurrency load",
        recent_actions=[
            "Tuned socket connection pool concurrency",
            "Adjusted thread pool size to reduce latency bottlenecks",
            "Measured response latency under 500 concurrent connections",
        ],
    )
    assert aligned["is_goal_drifting"] is False

    # Drifting goal (Spec 35)
    drifting = GoalAlignmentAuditor.audit_goal_alignment(
        original_goal_description="Reduce API latency",
        recent_actions=[
            "Migrated billing database to external vendor",
            "Refactored user invoice templates",
            "Added stripe payment webhook validation",
        ],
    )
    assert drifting["is_goal_drifting"] is True

    # Proxy Gaming (Goodhart's Law) (Spec 37)
    gaming = GoalAlignmentAuditor.detect_proxy_gaming(
        true_objective_metric="production_error_rate",
        proxy_metric="reported_incident_count",
        true_metric_delta_pct=-15.0,  # True metric degraded by 15%
        proxy_metric_delta_pct=35.0,  # Proxy metric improved by 35%
    )
    assert gaming["is_proxy_gaming"] is True
    assert "METRIC_GAMING_RISK" in gaming["alert"]


def test_error_taxonomy_and_clustering():
    mgr = ErrorManager()

    # Record errors across categories
    e1 = mgr.record_error(
        category=ErrorCategory.PLANNING_ERROR,
        severity=ErrorSeverity.MEDIUM,
        description="Deployment duration exceeded plan by 300%",
        error_code="SCHEDULE_UNDERESTIMATE",
    )
    assert e1["category"] == "PLANNING_ERROR"

    # Repeat same error code 3 times to trigger recurring pattern (Spec 29, 31)
    mgr.record_error(
        ErrorCategory.PLANNING_ERROR, ErrorSeverity.MEDIUM, "Exceeded plan 2", "SCHEDULE_UNDERESTIMATE"
    )
    mgr.record_error(
        ErrorCategory.PLANNING_ERROR, ErrorSeverity.HIGH, "Exceeded plan 3", "SCHEDULE_UNDERESTIMATE"
    )

    clusters = mgr.get_clusters()
    target_cluster = next((c for c in clusters if c.pattern_name == "SCHEDULE_UNDERESTIMATE"), None)
    assert target_cluster is not None
    assert target_cluster.recurring_count == 3

    # Check heatmap (Spec 61)
    heatmap = mgr.get_error_heatmap()
    assert heatmap[ErrorCategory.PLANNING_ERROR.value] == 3


def test_rationalization_detector():
    detector = RationalizationDetector()

    # 3 failures explained away without behavior adjustment (Spec 71)
    detector.record_failure_explanation(
        "Deploy timeout", "Network was momentarily slow", behavior_adjusted=False
    )
    detector.record_failure_explanation(
        "Deploy timeout", "Transient packet drop in AWS", behavior_adjusted=False
    )
    res = detector.record_failure_explanation(
        "Deploy timeout", "Upstream cloud DNS delay", behavior_adjusted=False
    )

    assert res["is_rationalizing"] is True
    assert res["pattern_alert"] == "RATIONALIZATION_PATTERN"


def test_intervention_tracker():
    # Effective intervention
    res_eff = InterventionTracker.evaluate_intervention(
        intervention_name="Tune connection pool size",
        expected_metric_delta_pct=20.0,
        actual_metric_delta_pct=18.5,
    )
    assert res_eff["is_effective"] is True
    assert res_eff["status"] == "VERIFIED_EFFECTIVE"

    # Ineffective intervention (Spec 73)
    res_fail = InterventionTracker.evaluate_intervention(
        intervention_name="Restart worker pods",
        expected_metric_delta_pct=30.0,
        actual_metric_delta_pct=2.0,
    )
    assert res_fail["is_effective"] is False
    assert res_fail["status"] == "INEFFECTIVE_INTERVENTION"
