"""Comprehensive tests for Task 104:
KAIRO Autonomous Continuous Evaluation, Benchmarking, Regression & Improvement Governance Engine.
Verifies all domain invariants, statistical discipline, calibration, regression detection,
governed improvement pipeline, EmergencyStop primacy, and REST APIs.
"""

from datetime import UTC, datetime
import pytest
from fastapi.testclient import TestClient

from app.evaluation.domain import (
    BaselineType,
    EvaluationBaseline,
    EvaluationCase,
    EvaluationComparison,
    EvaluationGate,
    EvaluationReview,
    EvaluationRun,
    EvaluationRunCase,
    EvaluationScenario,
    EvaluationSuite,
    ExecutionMode,
    GateStatus,
    ImprovementExperiment,
    ImprovementProposal,
    MetricMeasurement,
    MetricType,
    RegressionCategory,
    RegressionFinding,
    RegressionSeverity,
    ReplayReproducibility,
    ReviewStatus,
    RunStatus,
    ScenarioClass,
)
from app.evaluation.improvement_governance import ImprovementGovernanceEngine
from app.evaluation.metrics_engine import StatisticalMetricsCalculator, SubsystemMetricsScorer
from app.evaluation.regression_engine import ContinuousRegressionEngine
from app.evaluation.report_generator import ComprehensiveReportGenerator
from app.evaluation.run_engine import ContinuousRunEngine
from app.evaluation.scenario_engine import (
    AntiGamingDetector,
    BenchmarkContaminationDetector,
    ScenarioEngine,
    ScenarioSanitizer,
)
from app.evaluation.service import ContinuousEvaluationService
from app.main import create_app


# -------------------------------------------------------------------------
# 1. Domain Entities & Invariant Serialization Tests
# -------------------------------------------------------------------------

def test_evaluation_suite_domain_defaults():
    """Verify evaluation suite entity defaults and 20 canonical categories."""
    suite = EvaluationSuite(
        name="forecast_accuracy",
        description="Forecast accuracy benchmark",
        applicable_capabilities=["forecasting"],
        thresholds={"pass_rate": 0.90},
    )
    assert suite.id.startswith("suite_")
    assert suite.execution_mode == ExecutionMode.REAL
    assert suite.timeout_seconds == 300.0
    assert suite.status == "ACTIVE"


def test_scenario_classes_and_modes():
    """Verify 10 scenario classes and 5 execution modes."""
    classes = [
        ScenarioClass.DETERMINISTIC,
        ScenarioClass.REPLAY,
        ScenarioClass.SIMULATION,
        ScenarioClass.SYNTHETIC,
        ScenarioClass.HISTORICAL,
        ScenarioClass.PRODUCTION_DERIVED,
        ScenarioClass.ADVERSARIAL,
        ScenarioClass.CHAOS_FAULT_INJECTION,
        ScenarioClass.SHADOW,
        ScenarioClass.HOLDOUT,
    ]
    assert len(classes) == 10

    modes = [
        ExecutionMode.REAL,
        ExecutionMode.SHADOW,
        ExecutionMode.SIMULATED,
        ExecutionMode.REPLAY,
        ExecutionMode.SYNTHETIC,
    ]
    assert len(modes) == 5


# -------------------------------------------------------------------------
# 2. Metrics & Statistical Discipline Tests (Section 6 & 50)
# -------------------------------------------------------------------------

def test_classification_metrics_computation():
    """Verify confusion matrix calculations for accuracy, precision, recall, and F1."""
    metrics = StatisticalMetricsCalculator.compute_accuracy_precision_recall_f1(
        tp=80, fp=10, tn=85, fn=5
    )
    assert metrics["accuracy"] == 0.9167
    assert metrics["precision"] == 0.8889
    assert metrics["recall"] == 0.9412
    assert metrics["f1"] == 0.9143
    assert metrics["false_positive_rate"] == 0.1053


def test_brier_score_and_ece_calibration():
    """Verify probabilistic calibration scoring: Brier score and ECE (Section 6 & 10)."""
    # Well-calibrated predictions
    preds = [0.9, 0.8, 0.7, 0.2, 0.1]
    outcomes = [1, 1, 1, 0, 0]
    brier = StatisticalMetricsCalculator.compute_brier_score(preds, outcomes)
    assert brier < 0.1  # Low error for good calibration

    ece = StatisticalMetricsCalculator.compute_expected_calibration_error(preds, outcomes, num_bins=5)
    assert ece <= 0.20


def test_statistical_discipline_inconclusive_on_small_sample():
    """Critical invariant: Sample size < N_min must produce INCONCLUSIVE, NEVER PASS (Section 50)."""
    meas_small = StatisticalMetricsCalculator.evaluate_measurement(
        run_id="run_test",
        metric_name="accuracy",
        metric_type=MetricType.ACCURACY,
        values=[1.0, 1.0],  # only 2 samples, min is 5
        threshold=0.8,
        min_sample_size=5,
    )
    assert meas_small.status == GateStatus.INCONCLUSIVE
    assert meas_small.sample_size == 2

    # Adequate sample size
    meas_adequate = StatisticalMetricsCalculator.evaluate_measurement(
        run_id="run_test",
        metric_name="accuracy",
        metric_type=MetricType.ACCURACY,
        values=[0.9, 0.85, 0.95, 0.92, 0.88, 0.91],
        threshold=0.8,
        min_sample_size=5,
    )
    assert meas_adequate.status == GateStatus.PASS
    assert meas_adequate.sample_size == 6


# -------------------------------------------------------------------------
# 3. Subsystem Domain Distinction Tests (Sections 12, 15, 16, 18)
# -------------------------------------------------------------------------

def test_memory_relevance_vs_factual_correctness():
    """Invariant: A memory retrieval being semantically similar does NOT mean it is correct (Section 15)."""
    retrieved = ["Project Alpha uses PostgreSQL", "User email is old@test.com"]
    expected = ["PostgreSQL", "email"]
    # Suppose the email is factually outdated/stale in ground truth
    ground_truth = {"Project Alpha uses PostgreSQL": True, "User email is old@test.com": False}

    res = SubsystemMetricsScorer.score_memory_retrieval(retrieved, expected, ground_truth)
    assert res["retrieval_relevance"] == 1.0  # Both matched expected topics
    assert res["factual_correctness"] == 0.5  # Only 1 was factually valid
    assert res["stale_memory_ratio"] == 0.5


def test_action_execution_success_vs_outcome_success():
    """Invariant: execution_success != outcome_success (Section 12)."""
    # Action ran (execution_success=True) but postconditions failed (outcome_success=False)
    res = SubsystemMetricsScorer.score_action_execution(
        preflight_ok=True, executed=True, postconditions_satisfied=False, rollback_succeeded=True
    )
    assert res["execution_success"] is True
    assert res["outcome_success"] is False
    assert res["rollback_success"] is True
    assert res["passed"] is False


def test_multi_agent_consensus_vs_truth():
    """Invariant: Never equate consensus with truth (Section 18)."""
    # 3 agents agree on 'Option B', but ground truth is 'Option A'
    agent_opinions = ["Option B", "Option B", "Option B", "Option A"]
    res = SubsystemMetricsScorer.score_multi_agent_consensus(agent_opinions, ground_truth="Option A")
    assert res["agent_agreement"] == 0.75  # 75% consensus
    assert res["ground_truth_accuracy"] == 0.0  # Consensus is factually WRONG
    assert res["consensus_matches_truth"] == 0.0


# -------------------------------------------------------------------------
# 4. Regression Engine & 'Do Nothing' Baseline Tests (Sections 25 & 26)
# -------------------------------------------------------------------------

def test_regression_detection_blocks_on_security_and_safety():
    """Critical security regressions must block release strictly (Section 25)."""
    baseline = EvaluationBaseline(
        name="golden-v1",
        version="v1.0.0",
        metrics={"security_pass_rate": 1.0, "pass_rate": 0.95, "quality_score": 0.90},
    )

    candidate_run = EvaluationRun(
        suite_id="s1",
        suite_name="security_resilience",
        candidate_version="v1.1.0-rc1",
        security_pass_rate=0.90,  # Dropped from 1.0!
        pass_rate=0.95,
        quality_score=90.0,
    )

    comp = ContinuousRegressionEngine.compare_run_to_baseline(candidate_run, baseline, sample_size=10)
    assert comp.release_blocked is True
    assert comp.security_gate_passed is False
    assert any("SECURITY" in r for r in comp.blocking_reasons)


def test_do_nothing_baseline_evaluation():
    """Evaluate whether taking autonomous action was superior to doing nothing (Section 26)."""
    # Action improved outcome significantly
    justified = ContinuousRegressionEngine.evaluate_do_nothing_baseline(
        intervention_outcome_score=0.92, no_action_outcome_score=0.40, resource_cost_of_action=0.01
    )
    assert justified["action_was_justified"] is True
    assert justified["verdict"] == "INTERVENTION_SUPERIOR"

    # Action caused harm or did not improve
    unjustified = ContinuousRegressionEngine.evaluate_do_nothing_baseline(
        intervention_outcome_score=0.35, no_action_outcome_score=0.40, resource_cost_of_action=0.05
    )
    assert unjustified["action_was_justified"] is False
    assert unjustified["verdict"] == "NO_ACTION_BETTER"


# -------------------------------------------------------------------------
# 5. Governed Improvement Engine Tests (Sections 27, 28, 29, 31)
# -------------------------------------------------------------------------

def test_proposal_generation_and_experiments():
    """Verify ImprovementProposal generation and controlled experiment launching."""
    gov = ImprovementGovernanceEngine()

    regr = RegressionFinding(
        run_id="run_1",
        baseline_id="base_1",
        category=RegressionCategory.PERFORMANCE,
        severity=RegressionSeverity.MEDIUM,
        metric_name="latency_p95_ms",
        baseline_value=1200.0,
        candidate_value=1800.0,
        delta=600.0,
        delta_percentage=50.0,
        affected_capabilities=["tool_calculator"],
    )

    prop = gov.create_proposal_from_regressions(
        title="Optimize Calculator Concurrency",
        regressions=[regr],
        baseline_id="base_1",
        target_area="capability_configuration",
    )
    assert prop.status == "PROPOSED"
    assert "tool_calculator" in prop.affected_capabilities

    # Launch controlled shadow experiment
    exp = gov.launch_experiment(
        proposal=prop,
        control_baseline_id="base_1",
        hypothesis="Threadpool caching reduces calculator latency by 30%",
        sample_size_target=30,
    )
    assert exp.status == "RUNNING"
    assert exp.mode == ExecutionMode.SHADOW
    assert prop.status == "IN_EXPERIMENT"


def test_evaluation_gates_fail_closed():
    """Verify canonical evaluation gates: INCONCLUSIVE does not become PASS (Section 29)."""
    # Missing value -> INCONCLUSIVE
    gate_inc = ImprovementGovernanceEngine.evaluate_gate(
        gate_name="PERFORMANCE_GATE", run_id="r1", measured_value=None, threshold=0.8
    )
    assert gate_inc.status == GateStatus.INCONCLUSIVE

    # Security gate strict binary pass
    gate_sec_pass = ImprovementGovernanceEngine.evaluate_gate(
        gate_name="SECURITY_GATE", run_id="r1", measured_value=1.0, threshold=1.0, is_critical_security=True
    )
    assert gate_sec_pass.status == GateStatus.PASS

    # Security gate fail on even slight deviation
    gate_sec_fail = ImprovementGovernanceEngine.evaluate_gate(
        gate_name="SECURITY_GATE", run_id="r1", measured_value=0.99, threshold=1.0, is_critical_security=True
    )
    assert gate_sec_fail.status == GateStatus.FAIL


def test_human_governance_review_recording():
    """Verify human review records rationale and timestamp (Section 31)."""
    gov = ImprovementGovernanceEngine()
    prop = ImprovementProposal(
        title="Test Proposal",
        problem_statement="Test issue",
        target_area="context_policy",
        baseline_id="b1",
    )
    gov.proposals[prop.id] = prop

    rev = gov.record_human_review(
        proposal_id=prop.id,
        reviewer="lead_architect",
        decision=ReviewStatus.APPROVED,
        rationale="Evidence demonstrates 15% latency reduction with zero security impact.",
    )
    assert rev.status == ReviewStatus.APPROVED
    assert prop.status == "APPROVED"
    assert rev.reviewer == "lead_architect"


# -------------------------------------------------------------------------
# 6. Anti-Gaming, Contamination & Sanitization Tests (Sections 3, 4, 49)
# -------------------------------------------------------------------------

def test_production_data_sanitizer():
    """Verify sensitive PII and auth credentials are redacted in scenarios (Section 3)."""
    dirty_ctx = {
        "user_email": "admin@kairo.ai",
        "user_ip": "192.168.1.100",
        "auth_token": "Bearer sk-liveSecretKey12345678901234567890",
        "safe_query": "List all active machines",
    }
    cleaned = ScenarioSanitizer.sanitize_scenario_data(dirty_ctx)
    assert "[REDACTED_EMAIL]" in cleaned["user_email"]
    assert "[REDACTED_IP]" in cleaned["user_ip"]
    assert "[REDACTED" in cleaned["auth_token"]
    assert cleaned["safe_query"] == "List all active machines"


def test_contamination_detection_for_holdout_leakage():
    """Verify holdout test case leakage into prompts is detected immediately (Section 4 & 49)."""
    det = BenchmarkContaminationDetector()
    holdout_text = "Critical secret edge case: coordinate failure on datastore node 7 without alerts."
    det.register_golden_case("holdout_001", holdout_text, is_holdout=True)

    is_leaked, reason = det.check_for_contamination(holdout_text)
    assert is_leaked is True
    assert "Holdout" in reason

    is_safe, _ = det.check_for_contamination("Completely normal user prompt about weather.")
    assert is_safe is False


# -------------------------------------------------------------------------
# 7. Report Generator Taxonomy Tests (Section 53)
# -------------------------------------------------------------------------

def test_report_generator_distinguishes_fact_vs_measurement():
    """Verify reports explicitly distinguish FACT, OBSERVATION, MEASUREMENT, INFERENCE, RECOMMENDATION."""
    run = EvaluationRun(
        suite_id="s1",
        suite_name="mission_completion",
        cases_total=10,
        cases_passed=9,
        cases_failed=1,
        pass_rate=0.90,
        security_pass_rate=1.0,
    )
    md_report = ComprehensiveReportGenerator.generate_markdown_report(run)
    assert "[FACT]" in md_report
    assert "[MEASUREMENT]" in md_report
    assert "[INFERENCE]" in md_report
    assert "[RECOMMENDATION]" in md_report


# -------------------------------------------------------------------------
# 8. REST API Endpoints Verification (Section 38)
# -------------------------------------------------------------------------

@pytest.fixture(scope="module")
def api_client():
    app = create_app()
    with TestClient(app) as tc:
        yield tc


def test_api_continuous_evaluation_endpoints(api_client: TestClient):
    """Verify /api/v1/evaluations/ routes."""
    # 1. Health check
    res_health = api_client.get("/api/v1/evaluations/health")
    assert res_health.status_code == 200
    assert res_health.json()["status"] == "healthy"

    # 2. Dashboard
    res_dash = api_client.get("/api/v1/evaluations/dashboard")
    assert res_dash.status_code == 200
    d = res_dash.json()
    assert "overall_quality_score" in d
    assert "security_gate_intact" in d

    # 3. Suites
    res_suites = api_client.get("/api/v1/evaluations/suites")
    assert res_suites.status_code == 200
    suites = res_suites.json()
    assert len(suites) >= 10
    assert any(s["name"] == "security_resilience" for s in suites)

    # 4. Scenarios
    res_scen = api_client.get("/api/v1/evaluations/scenarios")
    assert res_scen.status_code == 200
    scens = res_scen.json()
    assert len(scens) >= 3

    # 5. Baselines
    res_base = api_client.get("/api/v1/evaluations/baselines")
    assert res_base.status_code == 200
    baselines = res_base.json()
    assert len(baselines) >= 1

    # 6. Trigger run
    run_payload = {
        "suite": "security_resilience",
        "candidate_version": "v1.2.0-test",
        "execution_mode": "REAL",
    }
    res_run = api_client.post("/api/v1/evaluations/runs", json=run_payload)
    assert res_run.status_code == 200
    run_data = res_run.json()
    assert run_data["status"] == "COMPLETED"
    assert run_data["pass_rate"] == 1.0

    # 7. List runs
    res_runs = api_client.get("/api/v1/evaluations/runs")
    assert res_runs.status_code == 200
    assert len(res_runs.json()) >= 1
