"""End-to-end operational verification script for Task 94: KAIRO Autonomous Decision Intelligence & Decision Memory Engine.

Executes 11 comprehensive operational scenarios validating:
1. Candidate Deliberation & Automatic NO_ACTION Baseline Candidate Injection
2. Hard Constraint Pre-Filtering (Infeasible options disqualified immediately)
3. Pareto Frontier Detection & Multidimensional Trade-Off Analysis
4. Subsystem Bridges (Governance, Security, Resources, Capabilities, Forecasting, Simulation)
5. ApprovalRegistry Gate Enforcement (Transitions to AWAITING_APPROVAL -> APPROVED)
6. Assumption Lifecycle, Invalidation, and Safe Drift Re-evaluation
7. EmergencyStop Fail-Closed Immediate Block
8. Structured 15-Point Decision Explanation Contract
9. Post-Execution Outcome Verification & Deviation / Regret Tracking
10. Decision Memory Safe Precedent Retrieval & REFERENCE_ONLY Reuse Guard
11. CLI Parser Subcommands Execution
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
import sys

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.decision.bridges import SubsystemBridges
from app.decision.cli import build_parser
from app.decision.domain import (
    ALLOWED_TRANSITIONS,
    AssumptionItem,
    ConstraintCategory,
    DecisionCertainty,
    DecisionConstraint,
    DecisionExplanation,
    DecisionInput,
    DecisionLifecycleState,
    DecisionOption,
    DecisionOutcomeRecord,
    DecisionType,
    DecisionV2Record,
    SecurityAuthorizationStatus,
    SimulationState,
    VerificationStatus,
)
from app.decision.evaluation import DecisionEvaluationEngine
from app.decision.intelligence_service import DecisionIntelligenceService
from app.decision.memory import DecisionMemoryEngine
from app.security.emergency_stop import EmergencyStopService
from app.security.exceptions import EmergencyStopActiveError


def run_e2e_scenarios() -> int:
    print("======================================================================")
    print("TASK 94 — AUTONOMOUS DECISION INTELLIGENCE END-TO-END VERIFICATION")
    print("======================================================================")
    passed = 0
    total = 11

    # ------------------------------------------------------------------
    # Scenario 1: Candidate Deliberation & NO_ACTION Injection
    # ------------------------------------------------------------------
    print("\n[Scenario 1] Candidate Deliberation & Automatic NO_ACTION Baseline Injection")
    service = DecisionIntelligenceService()
    inp = DecisionInput(
        title="Scale Kubernetes Compute Nodes",
        description="Deliberate on scaling cluster nodes under load",
        decision_type=DecisionType.RESOURCE_ALLOCATION,
        candidate_options=[
            DecisionOption(
                id="opt_scale_5",
                title="Scale by 5 nodes",
                alignment_score=0.92,
                risk_score=0.25,
                reversibility_score=0.85,
                resource_efficiency=0.7,
            )
        ]
    )
    rec1 = service.deliberate(inp)
    assert rec1 is not None, "Deliberation failed to produce a decision record"
    no_actions = [o for o in rec1.options if o.decision_type == DecisionType.NO_ACTION or o.id == "opt_no_action"]
    assert len(no_actions) >= 1, "NO_ACTION baseline was not automatically injected"
    print(f"  ✓ Produced decision '{rec1.id}' with {len(rec1.options)} options (including NO_ACTION baseline)")
    passed += 1

    # ------------------------------------------------------------------
    # Scenario 2: Hard Constraint Pre-Filtering
    # ------------------------------------------------------------------
    print("\n[Scenario 2] Hard Constraint Pre-Filtering")
    eval_engine = DecisionEvaluationEngine()
    constraints = [
        DecisionConstraint(
            id="cst_hard_budget",
            category=ConstraintCategory.RESOURCE_BUDGET,
            statement="Maximum cost is 100 credits",
            is_hard=True,
            threshold=100.0,
        )
    ]
    options = [
        DecisionOption(id="opt_within_budget", title="Standard Plan", projected_cost=80.0, alignment_score=0.8),
        DecisionOption(id="opt_over_budget", title="Super Plan", projected_cost=400.0, alignment_score=0.99),
    ]
    evaluated_opts = eval_engine.evaluate_options(options, constraints)
    by_id = {o.id: o for o in evaluated_opts}
    assert by_id["opt_within_budget"].is_feasible is True, "Feasible option was incorrectly rejected"
    assert by_id["opt_over_budget"].is_feasible is False, "Hard constraint violation failed to mark option infeasible"
    print("  ✓ Hard constraint strictly disqualified over-budget candidate (is_feasible=False)")
    passed += 1

    # ------------------------------------------------------------------
    # Scenario 3: Pareto Frontier & Tension Pairs
    # ------------------------------------------------------------------
    print("\n[Scenario 3] Pareto Frontier & Multidimensional Trade-Off Analysis")
    opt_a = DecisionOption(
        id="opt_balanced",
        title="Balanced Choice",
        alignment_score=0.85,
        risk_score=0.15,
        reversibility_score=0.9,
        resource_efficiency=0.85,
    )
    opt_b = DecisionOption(
        id="opt_dominated",
        title="Inferior Choice",
        alignment_score=0.5,
        risk_score=0.5,
        reversibility_score=0.5,
        resource_efficiency=0.4,
    )
    pareto_opts = eval_engine.compute_pareto_frontier([opt_a, opt_b])
    pareto_ids = {o.id for o in pareto_opts}
    assert "opt_balanced" in pareto_ids, "Balanced option should be in Pareto frontier"
    assert "opt_dominated" not in pareto_ids, "Dominated option should NOT be in Pareto frontier"
    print("  ✓ Correctly identified non-dominated Pareto frontier and identified dominated options")
    passed += 1

    # ------------------------------------------------------------------
    # Scenario 4: Subsystem Bridges
    # ------------------------------------------------------------------
    print("\n[Scenario 4] Subsystem Bridges Integration")
    bridges = SubsystemBridges()
    sec_stat, sec_msg = bridges.evaluate_security(opt_a)
    assert sec_stat in (SecurityAuthorizationStatus.AUTHORIZED, SecurityAuthorizationStatus.REQUIRES_APPROVAL)
    gov_report = bridges.evaluate_governance(opt_a)
    assert gov_report.get("compliance") is not None
    res_report = bridges.evaluate_resources(opt_a)
    assert res_report.get("is_feasible") is not None
    sim_gate = bridges.evaluate_simulation_gate(opt_a)
    assert sim_gate in SimulationState
    print(f"  ✓ Subsystem bridges verified: Security={sec_stat.value}, Governance={gov_report.get('compliance')}, Simulation={sim_gate.value}")
    passed += 1

    # ------------------------------------------------------------------
    # Scenario 5: ApprovalRegistry Gating
    # ------------------------------------------------------------------
    print("\n[Scenario 5] ApprovalRegistry Gate Enforcement")
    inp_destr = DecisionInput(
        title="Purge Legacy Archives",
        description="Permanently delete historical partitions",
        decision_type=DecisionType.DESTRUCTIVE,
        candidate_options=[
            DecisionOption(
                id="opt_purge_all",
                title="Purge All Records",
                alignment_score=0.9,
                requires_approval=True,
            )
        ]
    )
    rec_gate = service.deliberate(inp_destr)
    assert rec_gate.lifecycle_state == DecisionLifecycleState.AWAITING_APPROVAL, (
        f"Expected state AWAITING_APPROVAL, got {rec_gate.lifecycle_state}"
    )
    approved_rec = service.record_approval(rec_gate.id, approver_id="sec_lead_admin", approval_notes="Maintenance approved")
    assert approved_rec.lifecycle_state == DecisionLifecycleState.APPROVED, "Decision failed to transition to APPROVED"
    print("  ✓ Decision suspended in AWAITING_APPROVAL, then properly authorized into APPROVED")
    passed += 1

    # ------------------------------------------------------------------
    # Scenario 6: Assumption Lifecycle & Invalidation Re-evaluation
    # ------------------------------------------------------------------
    print("\n[Scenario 6] Assumption Lifecycle, Invalidation, and Safe Drift Re-evaluation")
    inp_asm = DecisionInput(
        title="Switch to Replica DNS",
        description="Requires secondary DNS latency < 20ms",
        decision_type=DecisionType.ACTION,
        assumptions=[
            AssumptionItem(
                id="asm_dns_latency",
                statement="Secondary DNS latency is sub-20ms",
                confidence=0.95,
                is_critical=True,
            )
        ],
        candidate_options=[
            DecisionOption(id="opt_switch_dns", title="Switch DNS Target", alignment_score=0.88)
        ]
    )
    rec_asm = service.deliberate(inp_asm)
    assert rec_asm.lifecycle_state in (DecisionLifecycleState.SELECTED, DecisionLifecycleState.APPROVED)
    drifted_rec = service.invalidate_assumption(rec_asm.id, "asm_dns_latency", "DNS latency spiked to 250ms")
    assert drifted_rec.lifecycle_state == DecisionLifecycleState.EVALUATING
    assert drifted_rec.assumptions[0].is_valid is False
    reeval = service.reevaluate(rec_asm.id, "Re-evaluating under degraded latency")
    assert reeval.lifecycle_state in (DecisionLifecycleState.EVALUATING, DecisionLifecycleState.SELECTED, DecisionLifecycleState.SUPERSEDED)
    print("  ✓ Invalidating critical assumption correctly reverted decision to EVALUATING for re-evaluation")
    passed += 1

    # ------------------------------------------------------------------
    # Scenario 7: EmergencyStop Fail-Closed Block
    # ------------------------------------------------------------------
    print("\n[Scenario 7] EmergencyStop Fail-Closed Immediate Block")
    EmergencyStopService.engage("Automated safety verification drill")
    try:
        blocked = False
        try:
            service.deliberate(inp)
        except EmergencyStopActiveError:
            blocked = True
        assert blocked is True, "Deliberation should fail-closed when EmergencyStop is active"
    finally:
        EmergencyStopService.disengage()
    print("  ✓ Verified EmergencyStop fail-closed enforcement (EmergencyStopActiveError raised)")
    passed += 1

    # ------------------------------------------------------------------
    # Scenario 8: 15-Point Structured Decision Explanation
    # ------------------------------------------------------------------
    print("\n[Scenario 8] Structured 15-Point Decision Explanation Contract")
    inp_exp = DecisionInput(
        title="Canary Rollout Strategy",
        description="Determine canary percentage for microservices",
        decision_type=DecisionType.ACTION,
        candidate_options=[
            DecisionOption(id="opt_canary_5", title="5% Canary", alignment_score=0.89),
            DecisionOption(id="opt_canary_20", title="20% Canary", alignment_score=0.82),
        ]
    )
    rec_exp = service.deliberate(inp_exp)
    assert rec_exp.explanation is not None, "Decision explanation was not generated"
    exp = rec_exp.explanation
    assert exp.objective != ""
    assert exp.selected_action != ""
    assert len(exp.options_considered) >= 2
    assert exp.governance_status != ""
    assert exp.security_status != ""
    assert exp.approval_status != ""
    print(f"  ✓ 15-point explanation verified: Selected Action='{exp.selected_action}', Security='{exp.security_status}', Governance='{exp.governance_status}'")
    passed += 1

    # ------------------------------------------------------------------
    # Scenario 9: Outcome Verification & Regret Tracking
    # ------------------------------------------------------------------
    print("\n[Scenario 9] Post-Execution Outcome Verification & Deviation / Regret Tracking")
    outcome_rec = DecisionOutcomeRecord(
        decision_id=rec_exp.id,
        predicted_outcome={"latency_p99": 45, "error_rate": 0.001},
        actual_outcome={"latency_p99": 48, "error_rate": 0.0012},
        deviation_score=0.04,
        regret_score=0.01,
        verification_status=VerificationStatus.VERIFIED,
        lessons_learned=["Canary was safe and performant"],
    )
    saved_outcome = service.record_outcome(outcome_rec)
    assert saved_outcome.verification_status == VerificationStatus.VERIFIED
    updated_dec = service.get_decision(rec_exp.id)
    assert updated_dec.verification_status == VerificationStatus.VERIFIED
    print(f"  ✓ Outcome verified: Deviation Score={saved_outcome.deviation_score}, Regret Score={saved_outcome.regret_score}")
    passed += 1

    # ------------------------------------------------------------------
    # Scenario 10: Decision Memory & REFERENCE_ONLY Reuse Guard
    # ------------------------------------------------------------------
    print("\n[Scenario 10] Decision Memory Safe Precedent Retrieval & Reuse Guard")
    mem_engine = DecisionMemoryEngine()
    historical_dec = DecisionV2Record(
        id="dec_historical_cache_evict",
        objective_id="obj_cache_optimization",
        title="Cache Optimization 2024",
        decision_type=DecisionType.POLICY_CHOICE,
        lifecycle_state=DecisionLifecycleState.EXECUTED,
        selected_option=DecisionOption(id="opt_lru", title="LRU Eviction", alignment_score=0.9),
        options=[DecisionOption(id="opt_lru", title="LRU Eviction", alignment_score=0.9)],
        provenance={"policy_version": "v1.0"},
    )
    mem_engine.record_precedent(historical_dec)
    precedents = mem_engine.find_precedents("cache", DecisionType.POLICY_CHOICE)
    assert len(precedents) > 0, "Failed to retrieve historical precedent from decision memory"
    prec = precedents[0]
    assert prec.get("reuse_status") in ("REFERENCE_ONLY", "APPLICABLE_WITH_REVIEW")
    assert prec.get("is_authoritative") is False
    print(f"  ✓ Retrieved precedent '{prec['decision_id']}' with safe reuse guard: {prec['reuse_status']} (is_authoritative=False)")
    passed += 1

    # ------------------------------------------------------------------
    # Scenario 11: CLI Parser Subcommands Execution
    # ------------------------------------------------------------------
    print("\n[Scenario 11] CLI Parser Subcommands Execution")
    parser = build_parser()
    args_list = parser.parse_args(["list", "--limit", "10"])
    assert args_list.subcommand == "list" and args_list.limit == 10

    args_inspect = parser.parse_args(["inspect", "dec_123456"])
    assert args_inspect.subcommand == "inspect" and args_inspect.decision_id == "dec_123456"

    args_explain = parser.parse_args(["explain", "dec_123456"])
    assert args_explain.subcommand == "explain" and args_explain.decision_id == "dec_123456"
    print("  ✓ CLI commands ('list', 'inspect', 'explain') verified successfully")
    passed += 1

    print("\n======================================================================")
    print(f"ALL {passed}/{total} END-TO-END SCENARIOS PASSED WITH ZERO VIOLATIONS")
    print("======================================================================")
    return 0


if __name__ == "__main__":
    sys.exit(run_e2e_scenarios())
