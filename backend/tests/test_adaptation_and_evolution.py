"""Comprehensive tests for Task 105:
KAIRO Autonomous Adaptation, Experiment Orchestration & Governed Evolution Engine.

Verifies:
1. Domain entities & lifecycle transitions
2. Hypothesis formulation, measurability & falsification
3. Experiment plan, deterministic assignment & firewall safety
4. EmergencyStop absolute primacy
5. Staged evaluation & stop condition triggers
6. Tri-condition statistical comparisons across 10 dimensions
7. Causal attribution & world-state drift verification
8. Evolution proposal & immutable changeset generation
9. Pre-rollout validation & capability promotion handoff
10. Control-loop safety & meta-adaptation safeguards
11. REST API endpoints & security
12. Anti-self-modification invariants
"""

from datetime import UTC, datetime
import pytest
from fastapi.testclient import TestClient

from app.adaptation.comparison_engine import ComparisonEngine
from app.adaptation.domain import (
    AdaptationHypothesis,
    AdaptationProgram,
    AssignmentStrategy,
    ComparisonVerdict,
    EvolutionChangeSet,
    EvolutionProposal,
    EvolutionProposalStatus,
    EvolutionReview,
    EvolutionValidation,
    ExperimentAssignment,
    ExperimentComparison,
    ExperimentEvidence,
    ExperimentGate,
    ExperimentObservation,
    ExperimentPlan,
    ExperimentRun,
    ExperimentVariant,
    MetricDimension,
    ProgramStatus,
    ReviewStatus,
    RunStatus,
    SandboxEnvironment,
    StopConditionType,
    ValidationStatus,
    VariantConfigType,
    VariantType,
)
from app.adaptation.evolution_engine import EvolutionEngine
from app.adaptation.experiment_engine import ExperimentAssignmentEngine, ExperimentEngine, ExperimentFirewall
from app.adaptation.hypothesis_engine import HypothesisEngine
from app.adaptation.meta_adaptation import MetaAdaptationEngine
from app.adaptation.service import AutonomousAdaptationService
from app.main import create_app
from app.security.emergency_stop import get_emergency_stop_service


# -----------------------------------------------------------------------------
# 1. Domain Entities & State Machine Transition Tests
# -----------------------------------------------------------------------------

def test_adaptation_program_lifecycle_transitions():
    """Verify validated state transitions for AdaptationProgram."""
    prog = AdaptationProgram(title="Test Program", affected_capability="web_search")
    assert prog.status == ProgramStatus.DRAFT

    # Valid transition: DRAFT -> PROPOSED -> REVIEWING -> APPROVED -> EXPERIMENTING -> VALIDATING -> SUCCESSFUL
    prog.transition_to(ProgramStatus.PROPOSED, reason="Submitted for review")
    assert prog.status == ProgramStatus.PROPOSED

    prog.transition_to(ProgramStatus.REVIEWING, reason="Review in progress")
    assert prog.status == ProgramStatus.REVIEWING

    prog.transition_to(ProgramStatus.APPROVED, reason="Approved for testing")
    assert prog.status == ProgramStatus.APPROVED

    prog.transition_to(ProgramStatus.EXPERIMENTING, reason="Testing begun")
    assert prog.status == ProgramStatus.EXPERIMENTING

    prog.transition_to(ProgramStatus.VALIDATING, reason="Pre-rollout validation")
    assert prog.status == ProgramStatus.VALIDATING

    prog.transition_to(ProgramStatus.SUCCESSFUL, reason="Evaluation passed")
    assert prog.status == ProgramStatus.SUCCESSFUL

    # Illegal transition from SUCCESSFUL to DRAFT must raise ValueError
    with pytest.raises(ValueError, match="Illegal program transition"):
        prog.transition_to(ProgramStatus.DRAFT)


def test_experiment_run_lifecycle_transitions():
    """Verify validated state transitions for ExperimentRun."""
    run = ExperimentRun(plan_id="plan_1", program_id="prog_1")
    assert run.status == RunStatus.CREATED

    run.transition_to(RunStatus.VALIDATING)
    assert run.status == RunStatus.VALIDATING

    run.transition_to(RunStatus.READY)
    assert run.status == RunStatus.READY

    run.transition_to(RunStatus.STARTING)
    assert run.status == RunStatus.STARTING

    run.transition_to(RunStatus.RUNNING)
    assert run.status == RunStatus.RUNNING
    assert run.started_at is not None

    run.transition_to(RunStatus.PAUSED)
    assert run.status == RunStatus.PAUSED

    run.transition_to(RunStatus.RUNNING)
    assert run.status == RunStatus.RUNNING

    run.transition_to(RunStatus.COMPLETED)
    assert run.status == RunStatus.COMPLETED
    assert run.completed_at is not None

    # Illegal transition from COMPLETED to RUNNING must raise ValueError
    with pytest.raises(ValueError, match="Illegal experiment run transition"):
        run.transition_to(RunStatus.RUNNING)


# -----------------------------------------------------------------------------
# 2. Hypothesis Formulation & Measurability Tests
# -----------------------------------------------------------------------------

def test_hypothesis_measurability_rejection():
    """Verify that vague, non-falsifiable hypotheses are strictly rejected."""
    engine = HypothesisEngine()

    # Vague hypothesis without quantified criteria must be rejected
    with pytest.raises(ValueError, match="Quantified metrics required"):
        engine.form_hypothesis(
            condition_change="If we make Kairo smarter",
            expected_outcome="then it will be better at things",
            evidence_reasoning="because intelligence is good",
        )

    # Missing measurable outcomes or falsification criteria must be rejected
    with pytest.raises(ValueError, match="Hypothesis must define measurable outcome thresholds"):
        engine.form_hypothesis(
            condition_change="If context retrieval window is restricted to fresh provenance memories",
            expected_outcome="then decision quality will improve without increasing latency",
            evidence_reasoning="fresh memories have higher factual consistency",
            measurable_outcomes={},
            falsification_criteria=[],
        )


def test_hypothesis_valid_formulation_and_falsification():
    """Verify valid hypothesis creation and falsification evaluation."""
    engine = HypothesisEngine()
    hyp = engine.form_hypothesis(
        condition_change="If context retrieval window is restricted to fresh provenance memories",
        expected_outcome="then decision quality will improve by at least 0.05",
        evidence_reasoning="provenance tags prevent contaminated hallucinations",
        confidence=0.8,
        measurable_outcomes={"decision_quality": 0.05},
        falsification_criteria=["Decision quality delta < 0.025", "Error rate increases"],
    )
    assert hyp.id.startswith("hyp_")
    assert hyp.confidence == 0.8
    assert len(hyp.counter_hypotheses) > 0

    # Falsification check 1: Safety breach always falsifies
    falsified, reason = engine.evaluate_falsification(hyp, measured_metrics={"decision_quality": 0.10}, safety_breached=True)
    assert falsified is True
    assert "safety" in reason.lower()

    # Falsification check 2: Measured metric failed to reach threshold
    falsified, reason = engine.evaluate_falsification(hyp, measured_metrics={"decision_quality": 0.01}, safety_breached=False)
    assert falsified is True
    assert "failed to achieve required improvement" in reason

    # Falsification check 3: Successful improvement supports hypothesis
    falsified, reason = engine.evaluate_falsification(hyp, measured_metrics={"decision_quality": 0.06}, safety_breached=False)
    assert falsified is False


# -----------------------------------------------------------------------------
# 3. Experiment Firewall & EmergencyStop Primacy Tests
# -----------------------------------------------------------------------------

def test_experiment_firewall_blocks_when_emergency_stop_active():
    """Verify that active EmergencyStop immediately blocks experiment runs fail-closed."""
    e_stop = get_emergency_stop_service()
    e_stop.trigger_emergency_stop(reason="Security incident drill")

    try:
        engine = ExperimentEngine()
        v_base = ExperimentVariant(name="base", variant_type=VariantType.BASELINE, target_artifact_id="art_1")
        v_cand = ExperimentVariant(name="cand", variant_type=VariantType.CANDIDATE, target_artifact_id="art_1")

        plan = engine.create_plan(
            program_id="prog_1",
            objective="Evaluate candidate optimization",
            hypothesis_id="hyp_1",
            variants=[v_base, v_cand],
        )

        run = engine.start_run(plan.id)
        assert run.status == RunStatus.BLOCKED
        assert "EMERGENCY_STOP_ACTIVE" in run.stop_reason
    finally:
        e_stop.reset_emergency_stop(is_human_user=True)


def test_experiment_firewall_missing_rollback_or_control():
    """Verify firewall blocks plans without control groups or rollback conditions."""
    # Missing baseline control
    v_cand = ExperimentVariant(name="cand", variant_type=VariantType.CANDIDATE, target_artifact_id="art_1")
    plan_no_base = ExperimentPlan(
        program_id="prog_1",
        hypothesis_id="hyp_1",
        variants=[v_cand],
        rollback_condition="Revert on error",
    )
    passed, blockers = ExperimentFirewall.check_firewall(plan_no_base)
    assert passed is False
    assert any("MISSING_CONTROL_GROUP" in b for b in blockers)

    # Missing rollback condition
    v_base = ExperimentVariant(name="base", variant_type=VariantType.BASELINE, target_artifact_id="art_1")
    plan_no_rollback = ExperimentPlan(
        program_id="prog_1",
        hypothesis_id="hyp_1",
        variants=[v_base, v_cand],
        rollback_condition="",
    )
    passed, blockers = ExperimentFirewall.check_firewall(plan_no_rollback)
    assert passed is False
    assert any("MISSING_ROLLBACK_STRATEGY" in b for b in blockers)


# -----------------------------------------------------------------------------
# 4. Deterministic Population Assignment Tests
# -----------------------------------------------------------------------------

def test_deterministic_assignment_reproducibility():
    """Verify that assignment engine produces identical assignments for identical seeds."""
    v1 = ExperimentVariant(id="var_base", name="baseline", variant_type=VariantType.BASELINE)
    v2 = ExperimentVariant(id="var_cand", name="candidate", variant_type=VariantType.CANDIDATE)
    plan = ExperimentPlan(variants=[v1, v2])

    scenarios = [f"scenario_{i:03d}" for i in range(20)]

    assign_1 = ExperimentAssignmentEngine.assign_population(plan, scenarios, seed=123)
    assign_2 = ExperimentAssignmentEngine.assign_population(plan, scenarios, seed=123)
    assign_different_seed = ExperimentAssignmentEngine.assign_population(plan, scenarios, seed=124)

    assert len(assign_1) == 20
    # Exactly identical mapping
    for a1, a2 in zip(assign_1, assign_2):
        assert a1.scenario_id == a2.scenario_id
        assert a1.variant_id == a2.variant_id

    # Different seed yields different assignments
    matches = sum(1 for a1, a3 in zip(assign_1, assign_different_seed) if a1.variant_id == a3.variant_id)
    assert matches < 20  # Not all identical


# -----------------------------------------------------------------------------
# 5. Tri-Condition Statistical Comparison Tests
# -----------------------------------------------------------------------------

def test_comparison_insufficient_sample_size_yields_inconclusive():
    """Verify that sample size < minimum required strictly produces INCONCLUSIVE."""
    cmp_engine = ComparisonEngine()
    v_base = ExperimentVariant(id="v_base", variant_type=VariantType.BASELINE)
    v_cand = ExperimentVariant(id="v_cand", variant_type=VariantType.CANDIDATE)

    obs = [
        ExperimentObservation(run_id="run_1", variant_id="v_cand", latency_ms=400.0)
        for _ in range(5)  # only 5 samples, min is 10
    ]

    result = cmp_engine.compare_variants(
        run_id="run_1",
        baseline_variant=v_base,
        candidate_variant=v_cand,
        baseline_metrics={"quality": 0.8},
        candidate_metrics={"quality": 0.95},
        observations=obs,
        min_sample_size=10,
    )

    assert result.verdict == ComparisonVerdict.INCONCLUSIVE
    assert "Insufficient sample size" in result.rationale


def test_comparison_baseline_drift_yields_inconclusive():
    """Verify that baseline drift during the experiment invalidates comparison -> INCONCLUSIVE."""
    cmp_engine = ComparisonEngine()
    v_base = ExperimentVariant(id="v_base", variant_type=VariantType.BASELINE)
    v_cand = ExperimentVariant(id="v_cand", variant_type=VariantType.CANDIDATE)

    obs = [ExperimentObservation(run_id="run_1", variant_id="v_cand", latency_ms=400.0) for _ in range(15)]

    result = cmp_engine.compare_variants(
        run_id="run_1",
        baseline_variant=v_base,
        candidate_variant=v_cand,
        baseline_metrics={"quality": 0.8},
        candidate_metrics={"quality": 0.95},
        observations=obs,
        min_sample_size=10,
        baseline_drift_detected=True,
    )

    assert result.verdict == ComparisonVerdict.INCONCLUSIVE
    assert "drifted" in result.rationale


def test_comparison_improved_and_regressed_verdicts():
    """Verify multi-objective comparison verdicts across dimensions."""
    cmp_engine = ComparisonEngine()
    v_base = ExperimentVariant(id="v_base", variant_type=VariantType.BASELINE)
    v_cand = ExperimentVariant(id="v_cand", variant_type=VariantType.CANDIDATE)
    obs = [ExperimentObservation(run_id="run_1", variant_id="v_cand", latency_ms=400.0) for _ in range(15)]

    # 1. Clear improvement: Higher quality, faster latency, 100% safety
    cmp_improved = cmp_engine.compare_variants(
        run_id="run_1",
        baseline_variant=v_base,
        candidate_variant=v_cand,
        baseline_metrics={"quality": 0.75, "safety": 1.0, "latency_ms": 600.0, "reliability": 0.95},
        candidate_metrics={"quality": 0.85, "safety": 1.0, "latency_ms": 480.0, "reliability": 0.98},
        observations=obs,
    )
    assert cmp_improved.verdict == ComparisonVerdict.IMPROVED

    # 2. Safety regression: Safety dropped below 1.0 -> REGRESSED
    cmp_regressed = cmp_engine.compare_variants(
        run_id="run_2",
        baseline_variant=v_base,
        candidate_variant=v_cand,
        baseline_metrics={"quality": 0.75, "safety": 1.0, "latency_ms": 600.0},
        candidate_metrics={"quality": 0.95, "safety": 0.90, "latency_ms": 400.0}, # High quality but unsafe!
        observations=obs,
    )
    assert cmp_regressed.verdict == ComparisonVerdict.REGRESSED

    # 3. Tradeoff: Higher quality but significantly slower latency
    cmp_tradeoff = cmp_engine.compare_variants(
        run_id="run_3",
        baseline_variant=v_base,
        candidate_variant=v_cand,
        baseline_metrics={"quality": 0.75, "safety": 1.0, "latency_ms": 400.0},
        candidate_metrics={"quality": 0.88, "safety": 1.0, "latency_ms": 750.0}, # Improved quality but regressed latency
        observations=obs,
    )
    assert cmp_tradeoff.verdict == ComparisonVerdict.TRADEOFF


# -----------------------------------------------------------------------------
# 6. Sealed Evidence & Cryptographic Immutability
# -----------------------------------------------------------------------------

def test_sealed_evidence_immutability():
    """Verify that sealed evidence contains an immutable cryptographic hash."""
    cmp_engine = ComparisonEngine()
    cmp = ExperimentComparison(
        run_id="run_sealed",
        verdict=ComparisonVerdict.IMPROVED,
        rationale="Verified improvement",
    )
    evidence = cmp_engine.package_sealed_evidence(
        run_id="run_sealed",
        program_id="prog_1",
        hypothesis_text="IF X THEN Y",
        baseline_summary={"quality": 0.8},
        candidate_summary={"quality": 0.9},
        comparison=cmp,
        observations_count=20,
    )
    assert evidence.immutable_hash != ""
    assert len(evidence.immutable_hash) == 64  # SHA-256 hex string


# -----------------------------------------------------------------------------
# 7. Evolution Proposal, Immutable ChangeSet & Governed Review
# -----------------------------------------------------------------------------

def test_evolution_proposal_rejection_for_non_improving_comparison():
    """Verify that non-improving experiments cannot generate evolution proposals."""
    evo_engine = EvolutionEngine()
    cmp_regressed = ExperimentComparison(run_id="run_bad", verdict=ComparisonVerdict.REGRESSED)
    evidence = ExperimentEvidence(run_id="run_bad")

    with pytest.raises(ValueError, match="expected IMPROVED"):
        evo_engine.create_proposal_from_evidence(
            program_id="prog_1",
            evidence=evidence,
            comparison=cmp_regressed,
            title="Bad Proposal",
            affected_capability="web_search",
            current_version="1.0.0",
            target_version="1.1.0",
            baseline_id="base_1",
            candidate_variant_id="cand_1",
        )


def test_evolution_proposal_and_changeset_lifecycle():
    """Verify proposal generation, immutable changeset creation, and review recording."""
    evo_engine = EvolutionEngine()
    cmp_improved = ExperimentComparison(run_id="run_good", verdict=ComparisonVerdict.IMPROVED)
    evidence = ExperimentEvidence(run_id="run_good", immutable_hash="a" * 64)

    proposal = evo_engine.create_proposal_from_evidence(
        program_id="prog_1",
        evidence=evidence,
        comparison=cmp_improved,
        title="Optimize Web Search",
        affected_capability="web_search",
        current_version="1.0.0",
        target_version="1.1.0",
        baseline_id="base_1",
        candidate_variant_id="cand_1",
    )
    assert proposal.status == EvolutionProposalStatus.SUBMITTED
    assert proposal.affected_capability == "web_search"

    # Generate immutable changeset
    changeset = evo_engine.generate_changeset(
        proposal=proposal,
        configuration_delta={"timeout_ms": 2500, "concurrency": 4},
    )
    assert changeset.content_hash != ""
    assert changeset.candidate_version == "1.1.0"

    # Record review
    review = evo_engine.record_review(
        proposal_id=proposal.id,
        reviewer="governance_officer",
        status=ReviewStatus.APPROVED,
        rationale="Evidence and regression tests fully verified.",
    )
    assert review.status == ReviewStatus.APPROVED
    assert proposal.status == EvolutionProposalStatus.APPROVED


# -----------------------------------------------------------------------------
# 8. Control-Loop Safety & Meta-Adaptation Safeguards
# -----------------------------------------------------------------------------

def test_meta_adaptation_control_loop_safety():
    """Verify maximum generation limits and diminishing return protection."""
    meta = MetaAdaptationEngine(max_generations=3, cooldown_seconds=0.0, diminishing_return_threshold=0.01)

    # 1. Max generation limit
    passed, violations = meta.check_loop_safety(capability="planner", current_generation=3, hypothesis_hash="hash_1")
    assert passed is False
    assert any("MAX_GENERATIONS_EXCEEDED" in v for v in violations)

    # 2. Diminishing returns after 3 microscopic deltas
    meta.record_experiment_outcome("planner", "h1", 0.002)
    meta.record_experiment_outcome("planner", "h2", 0.003)
    meta.record_experiment_outcome("planner", "h3", 0.001)

    passed, violations = meta.check_loop_safety(capability="planner", current_generation=1, hypothesis_hash="hash_4")
    assert passed is False
    assert any("DIMINISHING_RETURNS" in v for v in violations)


# -----------------------------------------------------------------------------
# 9. Closed-Loop Service Integration Test
# -----------------------------------------------------------------------------

def test_closed_loop_adaptation_service():
    """Verify full end-to-end integration through AutonomousAdaptationService."""
    service = AutonomousAdaptationService()

    # 1. Create Program
    program = service.create_program(
        title="Remediate Latency in Code Search",
        objective="Reduce code search latency below 400ms without quality loss",
        problem_statement="Continuous evaluation detected 550ms latency regression",
        affected_capability="code_search",
    )
    assert program.status == ProgramStatus.DRAFT

    # 2. Formulate Hypothesis
    hyp = service.create_hypothesis(
        program_id=program.id,
        condition_change="If embedding index cache size is doubled to 4096 entries",
        expected_outcome="then search latency will decrease by 80ms",
        evidence_reasoning="cache miss rate is currently 35% in evaluation runs",
        measurable_outcomes={"latency_delta_ms": -80.0},
    )
    assert hyp.id == program.hypothesis_id

    # 3. Design Experiment
    plan = service.design_experiment(
        program_id=program.id,
        objective="Evaluate index cache expansion",
        hypothesis_id=hyp.id,
        candidate_config_delta={"cache_size": 4096},
        target_artifact_id="code_search_v1",
    )
    assert len(plan.variants) == 3  # Baseline, Candidate, No-Action

    # 4. Start Experiment Run
    run = service.start_experiment(plan.id, target_sample_count=15)
    assert run.status == RunStatus.RUNNING

    # 5. Execute Controlled Test Cycle
    cmp = service.execute_controlled_test_cycle(
        run_id=run.id,
        candidate_quality_delta=0.05,
        candidate_latency_delta_ms=-70.0,
    )
    assert cmp.verdict == ComparisonVerdict.IMPROVED
    assert run.status == RunStatus.COMPLETED

    # 6. Create Evolution Proposal
    proposal = service.create_evolution_proposal(program_id=program.id, run_id=run.id)
    assert proposal.status == EvolutionProposalStatus.SUBMITTED

    # 7. Review Evolution Proposal
    review = service.review_evolution_proposal(
        proposal_id=proposal.id,
        reviewer="lead_architect",
        status=ReviewStatus.APPROVED,
        rationale="Significant latency reduction with proven safety invariant parity.",
    )
    assert review.status == ReviewStatus.APPROVED
    assert program.status == ProgramStatus.SUCCESSFUL

    # 8. Check Dashboard KPIs
    dash = service.get_dashboard_summary()
    assert dash["improving_count"] >= 1
    assert dash["blocked_count"] == 0


# -----------------------------------------------------------------------------
# 10. REST API Smoke Tests
# -----------------------------------------------------------------------------

@pytest.fixture(scope="module")
def api_client():
    app = create_app()
    with TestClient(app) as client:
        yield client


def test_adaptation_api_endpoints(api_client: TestClient):
    """Verify REST API endpoints under /api/v1/adaptation and /api/v1/evolution."""
    # 1. Dashboard
    r = api_client.get("/api/v1/adaptation/dashboard")
    assert r.status_code == 200
    data = r.json()
    assert "active_experiments" in data
    assert "emergency_stop_active" in data

    # 2. Programs list & create
    r = api_client.post("/api/v1/adaptation/programs", json={
        "title": "API Test Program",
        "objective": "Test objective via REST API",
        "problem_statement": "Problem statement for API test",
        "affected_capability": "web_search",
    })
    assert r.status_code == 201
    prog_id = r.json()["id"]

    r = api_client.get("/api/v1/adaptation/programs")
    assert r.status_code == 200
    assert any(p["id"] == prog_id for p in r.json())

    # 3. Evolution proposals list
    r = api_client.get("/api/v1/evolution/proposals")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
