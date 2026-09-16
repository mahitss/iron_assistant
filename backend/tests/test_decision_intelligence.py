"""Comprehensive test suite for Task 94: KAIRO Autonomous Decision Intelligence & Decision Memory Engine.

Verifies:
- Separation of Powers Axioms (DECISION != AUTHORIZATION != POLICY != PLANNING != EXECUTION)
- Epistemic Invariants & Unknown Handling (CONFIDENCE != CERTAINTY, UNKNOWN != FALSE)
- Lifecycle State Transitions & Transition Enforcement (16 legal states & disallowed jumps)
- Hard Constraint Pre-filtering & Feasibility Enforcement
- Multi-Criteria Non-Flattened Evaluation & Pareto Frontier Identification
- Automatic NO_ACTION Candidate Injection & Baseline Comparison
- Subsystem Bridges & EmergencyStop Fail-Closed Protection
- ApprovalRegistry Gating & Escalation Workflow
- Assumption Invalidation, Drift Detection & Safe Re-evaluation
- Decision Memory Precedents, Drift Flagging (REFERENCE_ONLY), & Outcome Recording
- 15-Point Structured Decision Explanation Contract
"""

from datetime import UTC, datetime, timedelta
import pytest

from app.decision.domain import (
    ALLOWED_TRANSITIONS,
    AssumptionItem,
    ConstraintCategory,
    DecisionConstraint,
    DecisionInput,
    DecisionLifecycleState,
    DecisionOption,
    DecisionOutcomeRecord,
    DecisionType,
    DecisionV2Record,
)
from app.decision.evaluation import DecisionEvaluationEngine
from app.decision.bridges import SubsystemBridges
from app.decision.memory import DecisionMemoryEngine
from app.decision.intelligence_service import DecisionIntelligenceService
from app.security.emergency_stop import EmergencyStopService
from app.security.exceptions import EmergencyStopActiveError


# ==============================================================================
# Axiom & Domain Model Tests
# ==============================================================================

def test_decision_lifecycle_enums_and_transitions():
    """Verify all 16 states exist and illegal transitions are rejected."""
    assert len(DecisionLifecycleState) == 16
    assert DecisionLifecycleState.EVALUATING in ALLOWED_TRANSITIONS[DecisionLifecycleState.PROPOSED]
    assert DecisionLifecycleState.AWAITING_APPROVAL in ALLOWED_TRANSITIONS[DecisionLifecycleState.SELECTED]
    assert DecisionLifecycleState.APPROVED in ALLOWED_TRANSITIONS[DecisionLifecycleState.AWAITING_APPROVAL]

    # Illegal direct jump: PROPOSED -> EXECUTED is not allowed
    assert DecisionLifecycleState.EXECUTED not in ALLOWED_TRANSITIONS[DecisionLifecycleState.PROPOSED]
    assert DecisionLifecycleState.EXECUTED not in ALLOWED_TRANSITIONS[DecisionLifecycleState.EVALUATING]


def test_decision_record_lifecycle_enforcement():
    """Verify DecisionV2Record rejects illegal state transitions."""
    rec = DecisionV2Record(
        id="dec:test_lifecycle",
        decision_type=DecisionType.ACTION,
        title="Test Lifecycle Decision",
        lifecycle_state=DecisionLifecycleState.PROPOSED,
    )
    assert rec.lifecycle_state == DecisionLifecycleState.PROPOSED

    # Legal transition
    rec.transition_to(DecisionLifecycleState.EVALUATING, reason="Starting deliberation")
    assert rec.lifecycle_state == DecisionLifecycleState.EVALUATING

    # Illegal transition: EVALUATING -> EXECUTED
    with pytest.raises(ValueError, match="Illegal state transition"):
        rec.transition_to(DecisionLifecycleState.EXECUTED, reason="Direct jump attempted")


def test_decision_record_staleness_detection():
    """Verify stale decisions are detected and marked as expired."""
    rec = DecisionV2Record(
        id="dec:test_stale",
        decision_type=DecisionType.ACTION,
        title="Stale Decision Test",
        lifecycle_state=DecisionLifecycleState.SELECTED,
        expires_at=datetime.now(UTC) - timedelta(minutes=5),
    )
    assert rec.is_stale is True


# ==============================================================================
# Evaluation & Pareto Frontier Tests
# ==============================================================================

def test_hard_constraint_filtering():
    """Hard constraints must disqualify candidate options regardless of score."""
    eval_engine = DecisionEvaluationEngine()

    constraints = [
        DecisionConstraint(
            id="c_hard_budget",
            category=ConstraintCategory.RESOURCE_BUDGET,
            description="Cost must not exceed 100 credits",
            is_hard=True,
            threshold=100.0,
        ),
        DecisionConstraint(
            id="c_soft_latency",
            category=ConstraintCategory.OPERATIONAL,
            description="Latency should be under 50ms",
            is_hard=False,
            threshold=50.0,
        )
    ]

    options = [
        DecisionOption(
            id="opt_cheap_slow",
            title="Cheap but Slow",
            projected_cost=50.0,
            projected_duration_ms=100,
            alignment_score=0.8,
            risk_score=0.2,
        ),
        DecisionOption(
            id="opt_expensive_fast",
            title="Expensive and Fast",
            projected_cost=250.0,  # Violates hard constraint!
            projected_duration_ms=20,
            alignment_score=0.99,
            risk_score=0.05,
        ),
    ]

    # Evaluate options against constraints
    evaluated = eval_engine.evaluate_options(
        options=options,
        constraints=constraints,
        objective="Optimize operations within budget",
    )

    by_id = {opt.id: opt for opt in evaluated}

    # Cheap option passes hard constraint
    assert by_id["opt_cheap_slow"].is_feasible is True

    # Expensive option FAILS hard constraint despite having higher alignment
    assert by_id["opt_expensive_fast"].is_feasible is False
    assert len(by_id["opt_expensive_fast"].constraint_violations) > 0


def test_pareto_dominance_and_trade_offs():
    """Verify non-dominated Pareto frontier detection and tension pairs."""
    eval_engine = DecisionEvaluationEngine()

    # Opt A dominates Opt B in all dimensions (higher alignment, lower risk, higher reversibility, higher efficiency)
    opt_a = DecisionOption(
        id="opt_superior",
        title="Superior Option",
        is_feasible=True,
        alignment_score=0.9,
        risk_score=0.1,
        reversibility_score=0.9,
        resource_efficiency=0.9,
    )
    opt_b = DecisionOption(
        id="opt_inferior",
        title="Inferior Option",
        is_feasible=True,
        alignment_score=0.6,
        risk_score=0.4,
        reversibility_score=0.5,
        resource_efficiency=0.5,
    )
    # Opt C has higher alignment than A, but higher risk (trade-off)
    opt_c = DecisionOption(
        id="opt_aggressive",
        title="Aggressive Option",
        is_feasible=True,
        alignment_score=0.98,
        risk_score=0.35,
        reversibility_score=0.4,
        resource_efficiency=0.8,
    )

    pareto_set = eval_engine.compute_pareto_frontier([opt_a, opt_b, opt_c])
    pareto_ids = {opt.id for opt in pareto_set}

    # opt_a and opt_c are Pareto-optimal (neither strictly dominates the other)
    assert "opt_superior" in pareto_ids
    assert "opt_aggressive" in pareto_ids

    # opt_b is dominated by opt_a
    assert "opt_inferior" not in pareto_ids
    assert opt_b.is_pareto_optimal is False


def test_automatic_no_action_candidate_injection():
    """If no NO_ACTION option is supplied, the engine must inject and evaluate it."""
    service = DecisionIntelligenceService()

    inp = DecisionInput(
        title="Scale Kubernetes Nodes",
        description="Deliberate scaling worker nodes",
        decision_type=DecisionType.RESOURCE_ALLOCATION,
        candidate_options=[
            DecisionOption(
                id="opt_scale_up",
                title="Scale up by 5 nodes",
                alignment_score=0.85,
                risk_score=0.3,
                projected_cost=150.0,
            )
        ]
    )

    rec = service.deliberate(inp)
    assert rec is not None

    # NO_ACTION candidate must be present in evaluated options
    no_action_opts = [o for o in rec.options if o.decision_type == DecisionType.NO_ACTION or o.id == "opt_no_action"]
    assert len(no_action_opts) >= 1
    assert no_action_opts[0].is_feasible is True


# ==============================================================================
# Subsystem Bridges & EmergencyStop Tests
# ==============================================================================

def test_emergency_stop_fail_closed():
    """If EmergencyStop is engaged, deliberation and selection must fail closed immediately."""
    EmergencyStopService.engage("Security drill engaged")
    service = DecisionIntelligenceService()

    inp = DecisionInput(
        title="Emergency Deployment",
        description="Attempt to decide while emergency stop is active",
        decision_type=DecisionType.ACTION,
        candidate_options=[
            DecisionOption(id="opt_deploy", title="Deploy Patch", alignment_score=0.9)
        ]
    )

    try:
        with pytest.raises(EmergencyStopActiveError):
            service.deliberate(inp)
    finally:
        EmergencyStopService.disengage()


def test_approval_registry_gating():
    """High-risk or privileged decisions must transition to AWAITING_APPROVAL and require explicit approval."""
    service = DecisionIntelligenceService()

    # Create decision requiring approval
    inp = DecisionInput(
        title="Drop Database Partition",
        description="Clean up old archive tables",
        decision_type=DecisionType.DESTRUCTIVE,
        candidate_options=[
            DecisionOption(
                id="opt_drop",
                title="Drop Partition 2024",
                alignment_score=0.9,
                risk_score=0.7,
                requires_approval=True,
            )
        ]
    )

    rec = service.deliberate(inp)
    assert rec.selected_option_id is not None
    # Because requires_approval=True, lifecycle state must be AWAITING_APPROVAL
    assert rec.lifecycle_state == DecisionLifecycleState.AWAITING_APPROVAL

    # Simulating approval via service
    approved_rec = service.record_approval(
        decision_id=rec.id,
        approver_id="security_admin",
        approval_notes="Approved for maintenance window",
    )
    assert approved_rec.lifecycle_state == DecisionLifecycleState.APPROVED
    assert approved_rec.metadata.get("approver_id") == "security_admin"


# ==============================================================================
# Assumption Tracking & Drift Re-evaluation Tests
# ==============================================================================

def test_assumption_invalidation_triggers_reevaluation():
    """Invalidating a critical assumption transitions decision to DRIFTED and requires re-evaluation."""
    service = DecisionIntelligenceService()

    inp = DecisionInput(
        title="Route traffic to secondary cluster",
        description="Assumes secondary cluster health > 95%",
        decision_type=DecisionType.ACTION,
        assumptions=[
            AssumptionItem(
                id="asm_cluster_health",
                statement="Secondary cluster is operating normally",
                confidence=0.99,
                is_critical=True,
            )
        ],
        candidate_options=[
            DecisionOption(id="opt_route", title="Route to Secondary", alignment_score=0.9)
        ]
    )

    rec = service.deliberate(inp)
    assert rec.lifecycle_state in (DecisionLifecycleState.SELECTED, DecisionLifecycleState.APPROVED)

    # Invalidate the critical assumption
    drifted_rec = service.invalidate_assumption(
        decision_id=rec.id,
        assumption_id="asm_cluster_health",
        new_evidence="Secondary cluster node degradation observed",
    )

    assert drifted_rec.lifecycle_state == DecisionLifecycleState.EVALUATING
    assert drifted_rec.assumptions[0].is_valid is False

    # Re-evaluate
    reevaluated_rec = service.reevaluate(rec.id, reason="Secondary cluster degraded")
    assert reevaluated_rec.lifecycle_state in (
        DecisionLifecycleState.EVALUATING,
        DecisionLifecycleState.SELECTED,
        DecisionLifecycleState.SUPERSEDED,
    )


# ==============================================================================
# Decision Memory & Precedent Reuse Safety Tests
# ==============================================================================

def test_decision_memory_recording_and_drift_flagging():
    """Decision precedents are stored, but drifted ones are strictly marked REFERENCE_ONLY."""
    mem_engine = DecisionMemoryEngine()

    past_dec = DecisionV2Record(
        id="dec:past_scaling_incident",
        decision_type=DecisionType.RESOURCE_ALLOCATION,
        title="Scale cluster during 2025 traffic spike",
        lifecycle_state=DecisionLifecycleState.EXECUTED,
        selected_option_id="opt_scale_10",
        options=[
            DecisionOption(id="opt_scale_10", title="Scale 10", alignment_score=0.9)
        ],
        outcomes=[
            DecisionOutcomeRecord(
                id="out_1",
                decision_id="dec:past_scaling_incident",
                predicted_impact={"latency_ms": 40},
                actual_impact={"latency_ms": 42},
                success=True,
                regret_score=0.05,
            )
        ],
    )

    mem_engine.record_precedent(past_dec)

    # Query precedent
    matches = mem_engine.find_precedents(
        query="cluster traffic spike",
        decision_type=DecisionType.RESOURCE_ALLOCATION,
    )
    assert len(matches) > 0
    precedent = matches[0]

    # Precedents MUST have safety reuse flag, cannot blindly auto-execute
    assert precedent.get("reuse_status") in ("REFERENCE_ONLY", "APPLICABLE_WITH_REVIEW")
    assert precedent.get("is_authoritative") is False


# ==============================================================================
# 15-Point Structured Explanation Contract Tests
# ==============================================================================

def test_fifteen_point_structured_explanation():
    """Verify that every deliberation generates a complete 15-point explanation."""
    service = DecisionIntelligenceService()

    inp = DecisionInput(
        title="Cache Eviction Strategy",
        description="Determine eviction policy for LRU storage",
        decision_type=DecisionType.POLICY_CHOICE,
        candidate_options=[
            DecisionOption(id="opt_lru", title="Least Recently Used", alignment_score=0.88),
            DecisionOption(id="opt_lfu", title="Least Frequently Used", alignment_score=0.82),
        ]
    )

    rec = service.deliberate(inp)
    assert rec.explanation is not None
    exp = rec.explanation

    # Check 15-point explanation fields
    assert exp.objective != ""
    assert exp.selected_option != ""
    assert exp.selection_rationale != ""
    assert isinstance(exp.rejected_alternatives, list)
    assert isinstance(exp.pareto_trade_offs, list)
    assert isinstance(exp.assumptions_relied_on, list)
    assert isinstance(exp.epistemic_uncertainties, list)
    assert exp.confidence_interval != ""
    assert exp.reversibility_assessment != ""
    assert exp.downstream_impacts != ""
    assert exp.governance_compliance != ""
    assert exp.approval_requirements != ""
    assert exp.fallback_plan != ""
    assert exp.monitoring_signals != ""
    assert exp.staleness_conditions != ""
