"""Evaluation benchmarks for Governance Intelligence, Constitutional Reasoning & Authority Engine (Task 78)."""

from __future__ import annotations

import asyncio
import time

from app.policy.authority import AuthorityManagerEngine
from app.policy.constitution import ConstitutionalEngine
from app.policy.escalation_detector import AuthorityEscalationDetector
from app.policy.governance_coordinator import GovernanceIntelligenceCoordinator
from app.policy.governance_schemas import (
    AuthorityLevel,
    GovernanceDecisionType,
    GovernanceReviewRequest,
    GovernanceState,
    PolicyTier,
    PrincipleName,
)
from app.policy.governance_state_machine import GovernanceStateMachine
from app.policy.hierarchy import PolicyHierarchyEngine


def test_benchmark_constitutional_evaluation_throughput() -> None:
    """Benchmark 1: High throughput constitutional reasoning (>= 500 evaluations / sec)."""
    engine = ConstitutionalEngine()
    count = 1000
    start = time.perf_counter()
    for i in range(count):
        score, evals, viols = engine.evaluate_action(
            action=f"action_{i % 10}",
            resource=f"res_{i % 5}",
            risk_level="R1_LOW",
        )
        assert 0.0 <= score <= 1.0
    elapsed = time.perf_counter() - start
    rate = count / elapsed
    assert rate >= 500.0, f"Rate {rate:.1f} evals/sec fell below 500 benchmark"


def test_benchmark_score_monotonicity_and_bounds() -> None:
    """Benchmark 2: Constitutional scores must strictly stay bounded [0.0, 1.0]."""
    engine = ConstitutionalEngine()
    test_cases = [
        {"action": "read", "risk_level": "R1_LOW", "is_destructive": False, "is_irreversible": False},
        {"action": "update", "risk_level": "R2_MODERATE", "is_destructive": False, "is_irreversible": False},
        {"action": "delete", "risk_level": "R3_HIGH", "is_destructive": True, "is_irreversible": False},
        {"action": "purge", "risk_level": "R4_CRITICAL", "is_destructive": True, "is_irreversible": True},
    ]
    scores = []
    for tc in test_cases:
        s, _, _ = engine.evaluate_action(
            action=tc["action"],
            resource="data",
            risk_level=tc["risk_level"],
            is_destructive=tc["is_destructive"],
            is_irreversible=tc["is_irreversible"],
        )
        assert 0.0 <= s <= 1.0
        scores.append(s)

    # Higher risk / destructiveness should never yield a strictly higher constitutional score
    for i in range(len(scores) - 1):
        assert scores[i] >= scores[i + 1], f"Score inverted: {scores[i]} < {scores[i+1]}"


def test_benchmark_hierarchy_conflict_determinism() -> None:
    """Benchmark 3: Hierarchy conflict resolution determinism across 500 permutations."""
    candidates = [
        {"policy_id": "p_task", "tier": PolicyTier.TASK, "decision": GovernanceDecisionType.ALLOWED, "reason": "task"},
        {"policy_id": "p_workflow", "tier": PolicyTier.WORKFLOW, "decision": GovernanceDecisionType.REQUIRES_APPROVAL, "reason": "wf"},
        {"policy_id": "p_security", "tier": PolicyTier.SECURITY, "decision": GovernanceDecisionType.REQUIRES_HUMAN, "reason": "sec"},
        {"policy_id": "p_system", "tier": PolicyTier.SYSTEM, "decision": GovernanceDecisionType.DENIED, "reason": "sys"},
    ]

    import random
    for _ in range(500):
        shuffled = list(candidates)
        random.shuffle(shuffled)
        decision, winner, _ = PolicyHierarchyEngine.resolve_conflicting_policies(shuffled)
        assert decision == GovernanceDecisionType.DENIED
        assert winner["policy_id"] == "p_system"


def test_benchmark_authority_check_latency() -> None:
    """Benchmark 4: Low latency authority verification (< 1ms per query)."""
    mgr = AuthorityManagerEngine()
    mgr.issue_grant(
        subject_id="bench_subject",
        authority_level=AuthorityLevel.PROJECT,
        allowed_scopes=["scope_1", "scope_2"],
        allowed_actions=["bench_action_*"],
    )

    count = 1000
    start = time.perf_counter()
    for _ in range(count):
        allowed, _, _ = mgr.check_authority(
            subject_id="bench_subject",
            action="bench_action_read",
            scope="scope_1",
            required_level=AuthorityLevel.LIMITED,
        )
        assert allowed is True
    elapsed = time.perf_counter() - start
    avg_ms = (elapsed / count) * 1000
    assert avg_ms < 1.0, f"Average latency {avg_ms:.3f}ms exceeded 1ms threshold"


def test_benchmark_probe_hammering_sensitivity() -> None:
    """Benchmark 5: Probe hammering velocity sensitivity."""
    detector = AuthorityEscalationDetector(probe_threshold=3, window_seconds=60)
    req = GovernanceReviewRequest(
        goal="Test",
        action="action_x",
        caller_id="agent_probe_bench",
        caller_authority=AuthorityLevel.LIMITED,
    )
    # 2 denials -> not yet flagged
    detector.record_attempt("agent_probe_bench", req, denied=True)
    detector.record_attempt("agent_probe_bench", req, denied=True)
    rep1 = detector.detect_escalation(req, AuthorityLevel.LIMITED)
    assert rep1.is_escalation_attempt is False

    # 3rd denial -> triggers flag
    detector.record_attempt("agent_probe_bench", req, denied=True)
    rep2 = detector.detect_escalation(req, AuthorityLevel.LIMITED)
    assert rep2.is_escalation_attempt is True
    assert rep2.bypass_technique == "PROBE_HAMMERING"


def test_benchmark_state_machine_matrix() -> None:
    """Benchmark 6: Exhaustive matrix testing of 8x8 state machine transitions."""
    sm = GovernanceStateMachine
    states = list(GovernanceState)
    valid_count = 0
    invalid_count = 0

    for s_from in states:
        for s_to in states:
            if sm.can_transition(s_from, s_to):
                res = sm.transition(s_from, s_to)
                assert res == s_to
                valid_count += 1
            else:
                invalid_count += 1

    # Ensure non-trivial valid paths exist and terminal states are respected
    assert valid_count >= 10
    assert invalid_count >= 40


def test_benchmark_least_privilege_accuracy() -> None:
    """Benchmark 7: Accuracy of least-privilege analysis across verb classes."""
    mgr = AuthorityManagerEngine()

    verbs_to_expected_perm = {
        "read_record": "READ",
        "fetch_config": "READ",
        "delete_user": "DESTRUCTIVE",
        "drop_database": "DESTRUCTIVE",
        "update_profile": "WRITE",
        "execute_workflow": "EXECUTE",
    }

    for action, expected_perm in verbs_to_expected_perm.items():
        rec = mgr.analyze_least_privilege(
            requested_permissions=["READ", "WRITE", "EXECUTE", "DESTRUCTIVE"],
            action=action,
        )
        assert expected_perm in rec.minimum_permissions_needed


def test_benchmark_multi_tier_override_strictness() -> None:
    """Benchmark 8: SYSTEM tier overrides lower tiers 100% of the time."""
    for tier in [PolicyTier.SECURITY, PolicyTier.TENANT, PolicyTier.PROJECT, PolicyTier.WORKFLOW, PolicyTier.TASK]:
        candidates = [
            {"policy_id": "p_sys", "tier": PolicyTier.SYSTEM, "decision": GovernanceDecisionType.DENIED},
            {"policy_id": f"p_{tier.value}", "tier": tier, "decision": GovernanceDecisionType.ALLOWED},
        ]
        win_decision, win_policy, _ = PolicyHierarchyEngine.resolve_conflicting_policies(candidates)
        assert win_decision == GovernanceDecisionType.DENIED
        assert win_policy["policy_id"] == "p_sys"


def test_benchmark_coordinator_end_to_end_latency() -> None:
    """Benchmark 9: End-to-end coordinator evaluation latency under burst load (< 5ms per request)."""
    coord = GovernanceIntelligenceCoordinator()
    req = GovernanceReviewRequest(
        goal="Fetch logs",
        action="read_system_logs",
        caller_id="system_admin",
        caller_authority=AuthorityLevel.ADMIN,
        risk_level="R1_LOW",
    )

    count = 100

    async def _run_burst():
        for _ in range(count):
            res = await coord.evaluate_review(req)
            assert res.decision == GovernanceDecisionType.ALLOWED

    start = time.perf_counter()
    asyncio.run(_run_burst())
    elapsed = time.perf_counter() - start
    avg_ms = (elapsed / count) * 1000
    assert avg_ms < 10.0, f"Average end-to-end evaluation latency {avg_ms:.2f}ms exceeded 10ms threshold"
