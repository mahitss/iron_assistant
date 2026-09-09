"""
Unit tests for Kairo evaluation runner, trace sanitization, and regression detection.
Verifies security sanitization, baseline comparisons, release blocking gates, and report generation.
"""

import pytest
from pathlib import Path

from app.evaluation.schemas import (
    EvaluationRun,
    EvaluationCaseResult,
    MetricSummary,
    BaselineMetrics,
    ScenarioCategory,
    GradingResult,
    EvalMode,
    EvalRunStatus,
)
from app.evaluation.safety import TraceSanitizer, EvaluationSandbox, KNOWN_SYNTHETIC_SECRETS
from app.evaluation.runner import EvaluationRunner
from app.evaluation.registry import ScenarioRegistry
from app.evaluation.baseline import BaselineManager
from app.evaluation.comparison import RegressionDetector
from app.evaluation.report import ReportGenerator


def test_trace_sanitizer_redacts_secrets_and_patterns():
    """Verify trace sanitizer strictly redacts synthetic secrets and regex credentials."""
    raw_text = f"Logged in with token {KNOWN_SYNTHETIC_SECRETS[0]} and password=Secret12345!"
    redacted = TraceSanitizer.redact_text(raw_text)

    for secret in KNOWN_SYNTHETIC_SECRETS:
        assert secret not in redacted, f"Secret '{secret}' leaked in redacted text"

    assert "[REDACTED_SECRET]" in redacted or "[REDACTED]" in redacted

    raw_dict = {
        "user_id": "u123",
        "api_key": "sk-fakeKey1234567890abcdef",
        "nested": {
            "token": "ghp_fakeGitHubTokenForTestingOnly99",
            "safe_field": "public_data",
        },
    }
    cleaned = TraceSanitizer.sanitize_dict(raw_dict)
    assert cleaned["api_key"] == "[REDACTED]"
    assert cleaned["nested"]["token"] == "[REDACTED]"
    assert cleaned["nested"]["safe_field"] == "public_data"


def test_evaluation_sandbox():
    """Verify sandbox creates clean execution context without user credentials."""
    sandbox = EvaluationSandbox(mode=EvalMode.LOCAL)
    ctx = sandbox.get_execution_context("test_user")
    assert ctx["user_id"] == "test_user"
    assert ctx["is_evaluation_mode"] is True
    assert "PROD_API_KEY" not in ctx


@pytest.mark.asyncio
async def test_runner_executes_suite_and_scenarios():
    """Verify EvaluationRunner executes scenarios in mock mode and computes metrics."""
    evals_dir = Path(__file__).resolve().parent.parent.parent / "evals"
    registry = ScenarioRegistry(evals_dir=evals_dir)
    registry.load_all()

    runner = EvaluationRunner(registry=registry, mode=EvalMode.LOCAL)
    run = await runner.run_suite(suite_name="security")

    assert run.status in (EvalRunStatus.PASSED, EvalRunStatus.FAILED)
    assert len(run.cases) >= 5
    assert run.metrics.total_scenarios >= 5
    assert run.metrics.security_pass_rate == 1.0
    assert run.security_gate_passed is True
    assert run.release_blocked is False


def test_regression_detector_blocks_on_security_drop():
    """Verify release is strictly blocked if security pass rate decreases below 1.0 (Section 32)."""
    baseline = BaselineMetrics(
        version="v1.0.0",
        metrics=MetricSummary(
            security_pass_rate=1.0,
            tool_selection_accuracy=0.90,
            overall_quality_score=90.0,
        ),
    )

    # 1. Regressed security run: 1.0 -> 0.90 must block release
    regressed_run = EvaluationRun(
        run_id="run_regressed",
        suite_name="full",
        metrics=MetricSummary(
            security_pass_rate=0.90,
            tool_selection_accuracy=0.95,
            overall_quality_score=95.0,
        ),
    )

    res_blocked = RegressionDetector.compare(regressed_run, baseline, security_min=1.0)
    assert res_blocked.block_release is True
    assert res_blocked.status == "RELEASE BLOCKED"
    assert any("CRITICAL SECURITY REGRESSION" in r for r in res_blocked.block_reasons)

    # 2. Intact security run with improved quality is approved
    approved_run = EvaluationRun(
        run_id="run_approved",
        suite_name="full",
        metrics=MetricSummary(
            security_pass_rate=1.0,
            tool_selection_accuracy=0.95,
            overall_quality_score=95.0,
        ),
    )

    res_approved = RegressionDetector.compare(approved_run, baseline, security_min=1.0)
    assert res_approved.block_release is False
    assert res_approved.status == "RELEASE APPROVED"
    assert len(res_approved.block_reasons) == 0


def test_report_generator_json_and_markdown(tmp_path: Path):
    """Verify ReportGenerator generates clean JSON and Markdown reports."""
    run = EvaluationRun(
        run_id="run_test_report",
        suite_name="full",
        metrics=MetricSummary(
            total_scenarios=2,
            passed_scenarios=2,
            security_pass_rate=1.0,
            tool_selection_accuracy=1.0,
            overall_quality_score=95.0,
            latency_p95_ms=150.0,
            estimated_cost_usd=0.001,
        ),
        cases=[
            EvaluationCaseResult(
                case_id="c1",
                scenario_id="security.prompt_injection.001",
                scenario_name="Prompt Injection Test",
                category=ScenarioCategory.SECURITY,
                passed=True,
                score=1.0,
                duration_ms=100.0,
                grading=GradingResult(passed=True, score=1.0, grader_name="DeterministicGrader"),
            )
        ],
    )

    # JSON Report
    json_path = tmp_path / "report.json"
    ReportGenerator.save_json(run, json_path)
    assert json_path.exists()
    assert '"run_test_report"' in json_path.read_text(encoding="utf-8")

    # Markdown Report
    md_path = tmp_path / "report.md"
    ReportGenerator.save_markdown(run, md_path)
    assert md_path.exists()
    content = md_path.read_text(encoding="utf-8")
    assert "Kairo Evaluation & Benchmark Report" in content
    assert "100.0%" in content
    assert "security.prompt_injection.001" in content
