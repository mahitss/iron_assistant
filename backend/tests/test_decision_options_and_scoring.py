"""Tests for Option generation, completeness, and explainable scoring (Task 57)."""

from app.decision.options import OptionGenerator
from app.decision.schemas import CandidateOption, Objective, OptionType, ReversibilityLevel
from app.decision.scoring import OptionScorer


def test_option_space_completeness():
    generator = OptionGenerator()

    # User only provided a single custom option
    custom_options = [
        CandidateOption(
            name="Custom Patch Deployment",
            option_type=OptionType.STANDARD,
            metrics={"cost": 20.0, "latency": 25.0},
        )
    ]

    complete = generator.ensure_option_space(custom_options, request_intent="INCIDENT_REMEDIATION")
    types = {opt.option_type for opt in complete}

    # Invariant: Must guarantee NO_ACTION baseline, INFO_GATHERING, and diversity
    assert OptionType.NO_ACTION in types
    assert OptionType.INFO_GATHERING in types
    assert len(complete) >= 4


def test_explainable_scoring_and_breakdown():
    scorer = OptionScorer()

    opt_good = CandidateOption(
        name="Balanced Canary Rollout",
        reversibility=ReversibilityLevel.REVERSIBLE,
        metrics={"reliability": 0.95, "security": 0.92, "cost": 30.0, "risk": 0.15},
    )

    objectives = [
        Objective(name="RELIABILITY", direction="MAXIMIZE", weight=0.5),
        Objective(name="SECURITY", direction="MAXIMIZE", weight=0.5),
    ]

    eval_good = scorer.evaluate_option(opt_good, objectives)
    assert eval_good.raw_score > 0.0
    assert eval_good.benefit_score > 0.8
    assert eval_good.reversibility_bonus > 0.0
    assert "objective_alignment" in eval_good.score_breakdown
    assert "risk_penalty" in eval_good.score_breakdown
    assert "Composite score" in eval_good.explanation


def test_disqualified_option_receives_zero_score():
    scorer = OptionScorer()

    opt_infeasible = CandidateOption(
        name="Unbudgeted Architecture Overhaul",
        is_feasible=False,
        hard_constraints_satisfied=False,
        rejection_reason="Violated hard budget constraint.",
        metrics={"reliability": 0.99, "security": 0.99},
    )

    objectives = [
        Objective(name="RELIABILITY", direction="MAXIMIZE", weight=0.5),
        Objective(name="SECURITY", direction="MAXIMIZE", weight=0.5),
    ]

    eval_res = scorer.evaluate_option(opt_infeasible, objectives)
    # High reliability cannot compensate for hard constraint violation
    assert eval_res.raw_score == 0.0
    assert eval_res.normalized_score == 0.0
    assert eval_res.rank == 999
    assert "Option disqualified" in eval_res.explanation


def test_score_normalization():
    scorer = OptionScorer()

    opt_a = CandidateOption(
        name="Option A",
        reversibility=ReversibilityLevel.REVERSIBLE,
        metrics={"reliability": 0.90, "security": 0.85, "cost": 20.0, "risk": 0.1},
    )
    opt_b = CandidateOption(
        name="Option B",
        reversibility=ReversibilityLevel.PARTIALLY_REVERSIBLE,
        metrics={"reliability": 0.70, "security": 0.70, "cost": 50.0, "risk": 0.3},
    )

    objectives = [
        Objective(name="RELIABILITY", direction="MAXIMIZE", weight=0.5),
        Objective(name="SECURITY", direction="MAXIMIZE", weight=0.5),
    ]

    evals = scorer.score_options([opt_a, opt_b], objectives)
    assert len(evals) == 2
    # The top feasible candidate should be normalized to 1.0
    assert evals[0].normalized_score == 1.0
    assert evals[1].normalized_score < 1.0
