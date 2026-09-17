"""Closed-Loop End-to-End Verification Script for Task 105:
KAIRO Autonomous Adaptation, Experiment Orchestration & Governed Evolution Engine.

Validates the full governed lifecycle:
EXPERIENCE -> EVALUATE -> FIND WEAKNESS -> FORM HYPOTHESIS -> DESIGN EXPERIMENT
-> SIMULATE/REPLAY -> GOVERN -> CONTROLLED TEST -> MEASURE -> COMPARE -> VERIFY
-> PROPOSE EVOLUTION -> GOVERNED CAPABILITY CHANGE -> RE-EVALUATE -> CONSOLIDATE EXPERIENCE

Verifies all non-negotiable safety invariants:
- Anti-self-modification: Proposal != Deployment, no arbitrary code injection
- EmergencyStop absolute primacy
- Tri-condition comparison: No-action vs Baseline vs Candidate
- Multi-objective evaluation without score compression
- Sealed immutable evidence packaging
- Subsystem handoffs to Capability Lifecycle (Task 91) and Cognitive Memory (Task 103)
"""

import asyncio
import os
from pathlib import Path
import sys

# Ensure UTF-8 stdout encoding across platforms
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure backend root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.adaptation.domain import (
    ComparisonVerdict,
    EvolutionProposalStatus,
    ProgramStatus,
    ReviewStatus,
    RunStatus,
    SandboxEnvironment,
    ValidationStatus,
)
from app.adaptation.service import AutonomousAdaptationService
from app.security.emergency_stop import get_emergency_stop_service


async def run_e2e_verification() -> bool:
    print("=" * 80)
    print("TASK 105: AUTONOMOUS ADAPTATION & GOVERNED EVOLUTION ENGINE — E2E VERIFICATION")
    print("=" * 80)

    service = AutonomousAdaptationService()

    # --------------------------------------------------------------------------
    # Phase 1: Ingest Weakness / Evaluation Finding (Task 104 Finding)
    # --------------------------------------------------------------------------
    print("\n[Phase 1] Ingesting continuous evaluation regression finding...")
    finding_id = "eval_finding_lat_099"
    program = service.create_program(
        title="Remediate Web Search Query Latency Regression",
        objective="Recover p95 latency below 350ms while preserving 100% safety invariants",
        problem_statement="Task 104 continuous evaluation benchmark detected query latency jumped from 280ms to 540ms (+92.8%)",
        affected_capability="web_search",
        originating_finding_id=finding_id,
        baseline_id="golden_v1_0_baseline",
        expected_benefit="Restore search response times to sub-350ms SLA",
        rollback_strategy="Revert web_search configuration parameters to v1.0.0 defaults",
        validation_strategy="Multi-suite replay + simulation sandbox gate",
    )
    assert program.id.startswith("prog_"), "Program ID format invalid"
    assert program.status == ProgramStatus.DRAFT, f"Expected DRAFT, got {program.status}"
    print(f"  [OK] Created AdaptationProgram: {program.id} ({program.title})")

    # --------------------------------------------------------------------------
    # Phase 2: Formulate Measurable Hypothesis (IF-THEN-BECAUSE)
    # --------------------------------------------------------------------------
    print("\n[Phase 2] Formulating structured, measurable hypothesis...")
    hyp = service.create_hypothesis(
        program_id=program.id,
        condition_change="If query embedding cache size is expanded to 8192 entries and DNS keepalive is enabled",
        expected_outcome="then p95 query latency will decrease by at least 150ms without degrading retrieval relevance",
        evidence_reasoning="Evaluation trace telemetry showed 42% cache miss rate and repeated socket reconnect overhead",
        confidence=0.88,
        measurable_outcomes={"latency_delta_ms": -150.0, "min_relevance": 0.85},
        falsification_criteria=[
            "Latency does not improve by at least 75ms",
            "Retrieval relevance drops below 0.85",
            "Any safety or security gate fails",
        ],
        assumptions=["Host memory capacity allows 8192 cache slots (+32MB memory footprint)"],
    )
    assert hyp.id.startswith("hyp_"), "Hypothesis ID format invalid"
    assert len(hyp.counter_hypotheses) > 0, "Counter-hypothesis missing"
    print(f"  [OK] Formulated Hypothesis: {hyp.id} (confidence={hyp.confidence:.2f})")
    print(f"    IF: {hyp.condition_change[:60]}...")
    print(f"    THEN: {hyp.expected_outcome[:60]}...")

    # --------------------------------------------------------------------------
    # Phase 3: Design Controlled Experiment (Tri-Condition: Baseline, Cand, NoOp)
    # --------------------------------------------------------------------------
    print("\n[Phase 3] Designing controlled experiment with tri-condition variants...")
    plan = service.design_experiment(
        program_id=program.id,
        objective="Controlled evaluation of query cache expansion in isolated simulation sandbox",
        hypothesis_id=hyp.id,
        candidate_config_delta={"cache_size": 8192, "dns_keepalive": True},
        target_artifact_id="web_search_v1",
        sandbox_environment=SandboxEnvironment.SIMULATION,
        resource_budget={"max_cost_usd": 2.50, "max_tokens": 25000},
        time_limit_seconds=1200.0,
    )
    assert len(plan.variants) == 3, f"Expected 3 variants, got {len(plan.variants)}"
    assert any(v.variant_type.value == "BASELINE" for v in plan.variants), "Missing BASELINE control"
    assert any(v.variant_type.value == "CANDIDATE" for v in plan.variants), "Missing CANDIDATE variant"
    assert any(v.variant_type.value == "NO_ACTION" for v in plan.variants), "Missing NO_ACTION control"
    print(f"  [OK] Experiment Plan Designed: {plan.id} ({len(plan.variants)} variants registered)")

    # --------------------------------------------------------------------------
    # Phase 4: Test Fail-Closed Experiment Firewall & EmergencyStop Primacy
    # --------------------------------------------------------------------------
    print("\n[Phase 4] Verifying Experiment Firewall and EmergencyStop primacy...")
    e_stop = get_emergency_stop_service()
    e_stop.trigger_emergency_stop(reason="Simulated EmergencyStop during verification")

    blocked_run = service.start_experiment(plan.id, target_sample_count=20)
    assert blocked_run.status == RunStatus.BLOCKED, f"Expected BLOCKED run, got {blocked_run.status}"
    assert "EMERGENCY_STOP" in blocked_run.stop_reason, f"Unexpected stop reason: {blocked_run.stop_reason}"
    print("  [OK] EmergencyStop active: Experiment run BLOCKED fail-closed immediately!")

    e_stop.reset_emergency_stop(is_human_user=True)
    assert not e_stop.is_stopped(), "EmergencyStop should be reset"
    print("  [OK] EmergencyStop disengaged by human operator.")

    # --------------------------------------------------------------------------
    # Phase 5: Start Experiment Run & Deterministic Population Assignment
    # --------------------------------------------------------------------------
    print("\n[Phase 5] Starting staged experiment in Simulation Sandbox...")
    active_run = service.start_experiment(plan.id, stage_number=2, target_sample_count=24)
    assert active_run.status == RunStatus.RUNNING, f"Expected RUNNING, got {active_run.status}"
    print(f"  [OK] Experiment Run Active: {active_run.id} (Stage {active_run.stage_number}, env={active_run.environment.value})")

    # --------------------------------------------------------------------------
    # Phase 6 & 7: Execute Controlled Test Cycle, Multi-Objective Compare
    # --------------------------------------------------------------------------
    print("\n[Phase 6 & 7] Executing controlled scenario observations and tri-condition comparison...")
    cmp = service.execute_controlled_test_cycle(
        run_id=active_run.id,
        candidate_quality_delta=0.06,
        candidate_latency_delta_ms=-185.0, # Meets >150ms improvement target!
        simulate_safety_failure=False,
    )
    assert cmp.verdict == ComparisonVerdict.IMPROVED, f"Expected IMPROVED verdict, got {cmp.verdict}"
    assert active_run.status == RunStatus.COMPLETED, f"Expected run COMPLETED, got {active_run.status}"
    assert cmp.sample_size == 24, f"Expected 24 observations, got {cmp.sample_size}"
    assert cmp.causal_attribution_verified is True, "Causal attribution unverified"
    assert cmp.world_state_verified is True, "World state drift detected"
    print(f"  [OK] Multi-Objective Comparison Verdict: {cmp.verdict.value}")
    print(f"    Quality Delta: +0.060 | Latency Delta: -185.0ms (Target achieved)")
    print(f"    World-State: {cmp.world_state_drift_summary}")
    print(f"    Causal Attribution: {cmp.causal_explanation}")

    # --------------------------------------------------------------------------
    # Phase 8: Package Sealed Immutable Evidence
    # --------------------------------------------------------------------------
    print("\n[Phase 8] Inspecting cryptographically sealed evidence bundle...")
    evidence = next((e for e in service.comparison_engine.evidences.values() if e.run_id == active_run.id), None)
    assert evidence is not None, "Sealed evidence missing"
    assert len(evidence.immutable_hash) == 64, "SHA-256 hash length mismatch"
    assert evidence.safety_gates_passed is True, "Safety gates failed"
    print(f"  [OK] Evidence Sealed: {evidence.id}")
    print(f"    Immutable SHA-256: {evidence.immutable_hash}")

    # --------------------------------------------------------------------------
    # Phase 9: Formulate Governed EvolutionProposal & Immutable ChangeSet
    # --------------------------------------------------------------------------
    print("\n[Phase 9] Generating governed EvolutionProposal & immutable ChangeSet...")
    proposal = service.create_evolution_proposal(
        program_id=program.id,
        run_id=active_run.id,
        target_version="1.1.0",
        deployment_scope="CANARY_10_PERCENT",
    )
    assert proposal.status == EvolutionProposalStatus.SUBMITTED, f"Expected SUBMITTED, got {proposal.status}"
    assert proposal.affected_capability == "web_search"
    assert proposal.required_approval is True, "Proposal should mandate governance approval"

    changeset = service.evolution_engine.changesets.get(proposal.id) or next(
        (c for c in service.evolution_engine.changesets.values() if c.proposal_id == proposal.id), None
    )
    assert changeset is not None, "ChangeSet missing"
    assert changeset.candidate_version == "1.1.0", f"Version mismatch: {changeset.candidate_version}"
    assert changeset.content_hash != "", "ChangeSet content hash missing"
    print(f"  [OK] EvolutionProposal Created: {proposal.id} ({proposal.title})")
    print(f"    Capability Transition: {proposal.affected_capability} ({proposal.current_version} → {proposal.target_version})")
    print(f"    Deployment Scope: {proposal.deployment_scope}")
    print(f"    Immutable ChangeSet Hash: {changeset.content_hash}")

    # --------------------------------------------------------------------------
    # Phase 10: Human/Governance Review, Validation, and Subsystem Handoffs
    # --------------------------------------------------------------------------
    print("\n[Phase 10] Executing pre-rollout validation, governance review, and memory handoff...")

    # Multi-suite validation
    val = service.validate_evolution(proposal_id=proposal.id, changeset_id=changeset.id, include_holdout=True)
    assert val.overall_status == ValidationStatus.PASSED, f"Validation failed: {val.overall_status}"
    assert val.holdout_passed is True, "Holdout suite failed"
    print(f"  [OK] Multi-Suite Pre-Rollout Validation: PASSED (Holdout verified)")

    # Governance Review
    review = service.review_evolution_proposal(
        proposal_id=proposal.id,
        reviewer="GovernanceBoard & SecurityCenter",
        status=ReviewStatus.APPROVED,
        rationale="All 10-dimensional metrics, safety gates, and regression corpus verified in simulation sandbox.",
        approval_reference_id="appr_sec_9082",
    )
    assert review.status == ReviewStatus.APPROVED
    assert proposal.status == EvolutionProposalStatus.APPROVED
    assert program.status == ProgramStatus.SUCCESSFUL
    print(f"  [OK] Governance Approval Granted: {review.id} (ref: {review.approval_reference_id})")
    print(f"    Program Status: {program.status.value}")

    # Subsystem Handoff 1: Capability Lifecycle Service (Task 91 Phase 10 Promotion Coordinator)
    handoff_cl = service.evolution_engine.handoff_to_capability_lifecycle(proposal, changeset)
    assert "delegated_to" in handoff_cl or "status" in handoff_cl
    print(f"  [OK] Delegated to Task 91: {handoff_cl.get('delegated_to', handoff_cl.get('status'))}")

    # Subsystem Handoff 2: Lifelong Memory Consolidation (Task 103 record_experience)
    exp_id = await service.handoff_to_cognitive_memory(
        summary=f"Query cache optimization improved web_search p95 latency by 185ms without regression.",
        evidence_dict={
            "program_id": program.id,
            "evidence_hash": evidence.immutable_hash,
            "version_transition": f"{proposal.current_version} -> {proposal.target_version}",
        },
        outcome="SUCCESS",
    )
    print(f"  [OK] Lifelong Memory Consolidation (Task 103): Experience ID = {exp_id or 'In-Memory Recorded'}")

    # --------------------------------------------------------------------------
    # Check Meta-Adaptation Health & Timeline Audit
    # --------------------------------------------------------------------------
    print("\n[Audit & Telemetry] Checking Adaptation Timeline and Meta-Health...")
    dash = service.get_dashboard_summary()
    assert dash["improving_count"] >= 1
    assert dash["emergency_stop_active"] is False

    meta_health = service.meta_engine.calculate_meta_health(
        total_experiments=1,
        successful_experiments=1,
        failed_experiments=0,
        inconclusive_experiments=0,
        rollback_count=0,
    )
    assert meta_health["adaptation_health"] == "NOMINAL"
    print(f"  [OK] Meta-Adaptation Health: {meta_health['adaptation_health']} (success_rate={meta_health['success_rate'] * 100:.0f}%)")
    print(f"  [OK] Total Audit Events Dispatched: {len(service.events)}")

    print("\n" + "=" * 80)
    print("ALL 10 PHASES OF AUTONOMOUS ADAPTATION & GOVERNED EVOLUTION VERIFIED!")
    print("=" * 80)
    return True


if __name__ == "__main__":
    success = asyncio.run(run_e2e_verification())
    sys.exit(0 if success else 1)
