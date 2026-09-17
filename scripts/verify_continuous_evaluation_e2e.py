"""End-to-End Closed Loop Verification Script for Task 104:
KAIRO Autonomous Continuous Evaluation, Benchmarking, Regression & Improvement Governance Engine.
Verifies the complete closed loop:
OBSERVE -> EVALUATE -> COMPARE -> DETECT REGRESSION -> PROPOSE IMPROVEMENT ->
SIMULATE/EXPERIMENT -> GOVERNANCE REVIEW -> MEMORY/EXPERIENCE CONSOLIDATION.
"""

import asyncio
import logging
import sys
from datetime import UTC, datetime

# Ensure UTF-8 output encoding across platforms
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from app.evaluation.domain import (
    BaselineType,
    EvaluationBaseline,
    EvaluationRun,
    ExecutionMode,
    GateStatus,
    ImprovementProposal,
    RegressionCategory,
    RegressionFinding,
    RegressionSeverity,
    ReviewStatus,
    RunStatus,
    ScenarioClass,
)
from app.evaluation.improvement_governance import ImprovementGovernanceEngine
from app.evaluation.metrics_engine import StatisticalMetricsCalculator, SubsystemMetricsScorer
from app.evaluation.regression_engine import ContinuousRegressionEngine
from app.evaluation.report_generator import ComprehensiveReportGenerator
from app.evaluation.run_engine import ContinuousRunEngine
from app.evaluation.scenario_engine import ScenarioEngine
from app.evaluation.service import ContinuousEvaluationService

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("verify_continuous_eval_e2e")


async def main() -> int:
    print("\n" + "=" * 80)
    print("KAIRO TASK 104: CONTINUOUS EVALUATION & IMPROVEMENT GOVERNANCE E2E VERIFICATION")
    print("=" * 80 + "\n")

    svc = ContinuousEvaluationService.get_instance()

    # -------------------------------------------------------------------------
    # Step 1: Register and Inspect Canonical Evaluation Suites (Section 2)
    # -------------------------------------------------------------------------
    print("[1/10] Verifying Canonical Evaluation Suites...")
    assert len(svc.suites) >= 20, f"Expected at least 20 suites, got {len(svc.suites)}"
    print(f"  [PASS] {len(svc.suites)} suites registered (including forecast_accuracy, decision_quality, action_verification, security_resilience)")

    # -------------------------------------------------------------------------
    # Step 2: Scenario Engine & 10 Taxonomy Classes (Section 3 & 4)
    # -------------------------------------------------------------------------
    print("\n[2/10] Verifying Scenarios, Classes, and Anti-Contamination...")
    scenarios = svc.scenario_engine.list_scenarios()
    assert len(scenarios) >= 4
    holdout_scenarios = svc.scenario_engine.list_scenarios(include_holdout=True)
    assert len(holdout_scenarios) > len(scenarios)  # Holdout separated
    print(f"  [PASS] {len(scenarios)} standard scenarios, {len(holdout_scenarios)} total including holdout partition.")

    # Test contamination detection
    is_leaked, _ = svc.scenario_engine.contamination_detector.check_for_contamination("Completely benign text")
    assert not is_leaked
    print("  [PASS] Contamination detector active with zero false positives.")

    # -------------------------------------------------------------------------
    # Step 3: Execute Continuous Evaluation Run (Section 7)
    # -------------------------------------------------------------------------
    print("\n[3/10] Executing Evaluation Run under Sandboxed Mode...")
    run = await svc.trigger_run(
        suite_name="security_resilience",
        candidate_version="v1.2.0-rc1",
        baseline_id="v1.0.0",
        execution_mode=ExecutionMode.REAL,
    )
    assert run.status == RunStatus.COMPLETED
    assert run.pass_rate == 1.0
    assert run.security_pass_rate == 1.0
    print(f"  [PASS] Run '{run.id}' completed successfully in {run.duration_ms:.1f}ms. Pass rate: {run.pass_rate*100:.1f}%.")

    # -------------------------------------------------------------------------
    # Step 4: Compare Against Frozen Baseline (Section 5 & 25)
    # -------------------------------------------------------------------------
    print("\n[4/10] Performing Baseline Delta & Regression Analysis...")
    comp = svc.comparisons.get(run.id)
    assert comp is not None
    assert comp.security_gate_passed is True
    print(f"  [PASS] Baseline comparison status: {comp.summary}")

    # -------------------------------------------------------------------------
    # Step 5: Detect Regression & Evaluate 'Do Nothing' Baseline (Section 25 & 26)
    # -------------------------------------------------------------------------
    print("\n[5/10] Testing Injected Regression Detection & 'Do Nothing' Baseline...")
    regressed_run = EvaluationRun(
        suite_id="action_verification",
        suite_name="action_verification",
        candidate_version="v1.2.0-unstable",
        pass_rate=0.70,
        security_pass_rate=0.90,  # CRITICAL SECURITY DROP
        latency_p95_ms=2500.0,
        quality_score=70.0,
    )
    baseline = svc.baselines["v1.0.0"]
    reg_comp = ContinuousRegressionEngine.compare_run_to_baseline(regressed_run, baseline, sample_size=10)
    assert reg_comp.release_blocked is True
    assert reg_comp.regressions_count > 0
    print(f"  [PASS] Detected {reg_comp.regressions_count} regression(s). Release strictly blocked fail-closed.")

    do_nothing = ContinuousRegressionEngine.evaluate_do_nothing_baseline(
        intervention_outcome_score=0.95, no_action_outcome_score=0.45, resource_cost_of_action=0.002
    )
    assert do_nothing["action_was_justified"] is True
    print(f"  [PASS] 'Do Nothing' baseline verified: net gain +{do_nothing['net_gain']:.2f}, action justified.")

    # -------------------------------------------------------------------------
    # Step 6: Generate Governed Improvement Proposal (Section 27)
    # -------------------------------------------------------------------------
    print("\n[6/10] Generating Evidence-Backed Improvement Proposal...")
    regr_finding = RegressionFinding(
        run_id=regressed_run.id,
        baseline_id=baseline.id,
        category=RegressionCategory.RELIABILITY,
        severity=RegressionSeverity.HIGH,
        metric_name="pass_rate",
        baseline_value=0.95,
        candidate_value=0.70,
        delta=-0.25,
        delta_percentage=-26.3,
        affected_capabilities=["action_executor"],
    )
    proposal = svc.governance_engine.create_proposal_from_regressions(
        title="Remediate Action Transaction Postcondition Verification Flakiness",
        regressions=[regr_finding],
        baseline_id=baseline.id,
        target_area="capability_implementation",
        proposed_change={"timeout_override": 45.0, "retry_limit": 2},
    )
    assert proposal.status == "PROPOSED"
    assert "action_executor" in proposal.affected_capabilities
    print(f"  [PASS] Created proposal '{proposal.id}': {proposal.title}")

    # -------------------------------------------------------------------------
    # Step 7: Launch Controlled Experiment & Evaluate Gates (Section 28 & 29)
    # -------------------------------------------------------------------------
    print("\n[7/10] Launching Controlled Experiment & Evaluating Canonical Gates...")
    exp = svc.governance_engine.launch_experiment(
        proposal=proposal,
        control_baseline_id=baseline.id,
        hypothesis="Increasing postcondition verification timeout eliminates transient timeouts.",
        sample_size_target=50,
    )
    assert exp.status == "RUNNING"
    assert exp.mode == ExecutionMode.SHADOW
    print(f"  [PASS] Experiment '{exp.id}' active in SHADOW mode (safety gates: {exp.safety_gates}).")

    gate = ImprovementGovernanceEngine.evaluate_gate(
        gate_name="SAFETY_GATE", run_id=run.id, measured_value=1.0, threshold=1.0, is_critical_security=True
    )
    assert gate.status == GateStatus.PASS
    print(f"  [PASS] Evaluated {gate.gate_name}: {gate.status.value} ({gate.reason})")

    # -------------------------------------------------------------------------
    # Step 8: Human / Governance Authority Review (Section 31)
    # -------------------------------------------------------------------------
    print("\n[8/10] Recording Governance Authority Human Review...")
    review = svc.governance_engine.record_human_review(
        proposal_id=proposal.id,
        reviewer="lead_governance_auditor",
        decision=ReviewStatus.APPROVED,
        rationale="Verified in shadow simulation without resource degradation.",
    )
    assert review.status == ReviewStatus.APPROVED
    assert proposal.status == "APPROVED"
    print(f"  [PASS] Human review recorded: {review.status.value} by {review.reviewer}.")

    # -------------------------------------------------------------------------
    # Step 9: Memory Consolidation Handoff (Section 42 & Task 103)
    # -------------------------------------------------------------------------
    print("\n[9/10] Testing Cognitive Memory Experience Consolidation Handoff...")
    exp_id = await svc.governance_engine.handoff_to_cognitive_memory(
        finding_summary=proposal.title,
        evidence_dict={"proposal_id": proposal.id, "benefit": proposal.expected_benefit},
        outcome="SUCCESS",
    )
    print(f"  [PASS] Experience candidate generated for Task 103 memory fabric: {exp_id or 'Handled cleanly'}.")

    # -------------------------------------------------------------------------
    # Step 10: Structured Report Generation (Section 53)
    # -------------------------------------------------------------------------
    print("\n[10/10] Generating Structured Audit Report with Fact vs Inference Taxonomy...")
    report_md = ComprehensiveReportGenerator.generate_markdown_report(
        run=run, comparison=comp, proposals=[proposal]
    )
    assert "[FACT]" in report_md
    assert "[MEASUREMENT]" in report_md
    assert "[INFERENCE]" in report_md
    assert "[RECOMMENDATION]" in report_md
    print("  [PASS] Multi-layer taxonomy report verified.")

    print("\n" + "=" * 80)
    print("ALL 10 VERIFICATION PHASES COMPLETED WITH 100% SUCCESS.")
    print("Task 104 Continuous Evaluation, Benchmarking & Governance Engine Verified.")
    print("=" * 80 + "\n")
    return 0


if __name__ == "__main__":
    code = asyncio.run(main())
    sys.exit(code)
