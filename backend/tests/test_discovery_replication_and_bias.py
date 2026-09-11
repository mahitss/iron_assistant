"""Unit tests for Experiment Replication, Conflict Detection, and Bias Auditing (Task 72)."""

from app.discovery.replication import (
    BiasDetector,
    ReplicationEngine,
    calculate_sample_statistics,
)
from app.discovery.schemas import (
    AnalysisOutcome,
    ExperimentResult,
    GeneralizationScope,
)


def test_replication_consistent_outcomes():
    """Consistent runs across trials are marked REPLICATED."""
    engine = ReplicationEngine()

    orig = ExperimentResult(
        result_id="res_orig",
        experiment_id="exp_orig",
        outcome=AnalysisOutcome.SUPPORTED,
        prediction_vs_observation_summary="Latency dropped 20%",
        effect_size=0.20,
        unexpected_anomaly_detected=False,
        new_hypotheses=[],
        is_valid=True,
        replication_status="SINGLE_RUN",
        generalization_scope=GeneralizationScope.ENVIRONMENT_SPECIFIC,
        conclusions=["Supported in Staging 1"],
    )

    replica = ExperimentResult(
        result_id="res_replica",
        experiment_id="exp_replica",
        outcome=AnalysisOutcome.SUPPORTED,
        prediction_vs_observation_summary="Latency dropped 22%",
        effect_size=0.22,
        unexpected_anomaly_detected=False,
        new_hypotheses=[],
        is_valid=True,
        replication_status="SINGLE_RUN",
        generalization_scope=GeneralizationScope.ENVIRONMENT_SPECIFIC,
        conclusions=["Supported in Staging 2"],
    )

    eval_data = engine.evaluate_replication(orig, replica)
    assert eval_data["status"] == "REPLICATED"
    assert eval_data["is_consistent"] is True
    assert orig.replication_status == "REPLICATED"
    assert replica.replication_status == "REPLICATED"


def test_replication_conflict_detection():
    """Conflicting trials surface REPLICATION_CONFLICT rather than silently averaging."""
    engine = ReplicationEngine()

    orig = ExperimentResult(
        result_id="res_orig",
        experiment_id="exp_orig",
        outcome=AnalysisOutcome.SUPPORTED,
        prediction_vs_observation_summary="Latency dropped 20%",
        effect_size=0.20,
        unexpected_anomaly_detected=False,
        new_hypotheses=[],
        is_valid=True,
        replication_status="SINGLE_RUN",
        generalization_scope=GeneralizationScope.ENVIRONMENT_SPECIFIC,
        conclusions=["Supported in Staging 1"],
    )

    replica = ExperimentResult(
        result_id="res_replica_bad",
        experiment_id="exp_replica_bad",
        outcome=AnalysisOutcome.CONTRADICTED,
        prediction_vs_observation_summary="Latency increased by 15%",
        effect_size=0.15,
        unexpected_anomaly_detected=False,
        new_hypotheses=[],
        is_valid=True,
        replication_status="SINGLE_RUN",
        generalization_scope=GeneralizationScope.ENVIRONMENT_SPECIFIC,
        conclusions=["Contradicted in Staging 2"],
    )

    eval_data = engine.evaluate_replication(orig, replica)
    assert eval_data["status"] == "REPLICATION_CONFLICT"
    assert eval_data["is_consistent"] is False
    assert "Outcome divergence" in eval_data["details"][0]
    assert orig.replication_status == "REPLICATION_CONFLICT"
    assert replica.replication_status == "REPLICATION_CONFLICT"


def test_cognitive_bias_auditing():
    """Detects confirmation bias and anchoring bias during discovery deliberation."""
    detector = BiasDetector()

    # Case 1: Confirmation bias: Hypothesis tested without attempting falsification
    tested_hyps = [
        {
            "hypothesis_id": "hyp_favored",
            "confidence": 0.8,
            "contradicting_evidence": [],
            "falsification_tested": False,
            "tested_first": True,
        }
    ]

    biases = detector.audit_biases(
        tested_hypotheses=tested_hyps,
        experiment_types_used=["OBSERVATIONAL"],
        results=[],
    )

    assert any("Confirmation Bias" in b for b in biases)


def test_factual_sample_statistics_calculation():
    """Calculates factual sample statistics without fake statistical significance."""
    stats = calculate_sample_statistics([10.0, 12.0, 14.0, 16.0, 18.0])

    assert stats["sample_size"] == 5
    assert stats["mean"] == 14.0
    assert stats["median"] == 14.0
    assert stats["variance"] == 10.0
    assert round(stats["std_dev"], 2) == 3.16

    empty_stats = calculate_sample_statistics([])
    assert empty_stats["sample_size"] == 0
    assert empty_stats["mean"] == 0.0
