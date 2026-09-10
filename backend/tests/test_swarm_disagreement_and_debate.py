"""Unit tests for Disagreement Detection, 10-Class Taxonomy, and Controlled Dialectical Debate (Task 64)."""

from app.swarm.debate import DebateEngine
from app.swarm.disagreement import DisagreementDetector
from app.swarm.schemas import (
    AgentAssertion,
    AgentResult,
    DebateStatus,
    DisagreementRecord,
    DisagreementType,
    EpistemicType,
    PeerReview,
    SwarmAgentSpec,
)


def test_disagreement_detection_from_peer_reviews():
    detector = DisagreementDetector()

    target_res = AgentResult(
        agent_id="agt_arch_01",
        task_id="tsk_arch",
        role="ARCHITECT",
        answer="Monolithic gateway satisfies all throughput latency objectives.",
        claims=[
            AgentAssertion(
                text="Monolith gateway satisfies sub-10ms latency.",
                epistemic_type=EpistemicType.CLAIM,
            )
        ],
        evidence=[{"type": "BENCHMARK", "source": "Internal Test"}],
    )

    review = PeerReview(
        reviewer_agent_id="agt_critic_01",
        reviewer_role="CRITIC",
        target_result_id=target_res.result_id,
        issues=["Under burst traffic, monolithic queue will stall worker processes."],
        counterarguments=[
            "Empirical stress tests demonstrate thread starvation under 30k concurrent sockets."
        ],
        severity="HIGH",
        recommendation="CONTEST",
        correctness_score=0.60,
    )

    disagreements = detector.detect_disagreements(
        results=[target_res],
        reviews=[review],
    )

    assert len(disagreements) >= 1
    d = disagreements[0]
    assert d.severity == "HIGH"
    assert "agt_critic_01" in d.involved_agent_ids
    assert "agt_arch_01" in d.involved_agent_ids
    assert d.category in [DisagreementType.CAUSAL, DisagreementType.ASSUMPTION, DisagreementType.EVIDENCE]


def test_10_class_disagreement_taxonomy_classification():
    detector = DisagreementDetector()
    dummy_res = AgentResult(
        agent_id="agt_01",
        task_id="tsk_01",
        role="ARCHITECT",
        answer="Initial architecture plan.",
    )

    # 1. CAUSAL
    cat = detector._classify_disagreement_nature(
        issues=["Causation between thread count and latency was misattributed."],
        counterarguments=[],
        target_result=dummy_res,
    )
    assert cat == DisagreementType.CAUSAL

    # 2. ASSUMPTION
    cat = detector._classify_disagreement_nature(
        issues=["Author assumes continuous network connectivity."],
        counterarguments=[],
        target_result=dummy_res,
    )
    assert cat == DisagreementType.ASSUMPTION

    # 3. EVIDENCE
    cat = detector._classify_disagreement_nature(
        issues=["Evidence cited is sparse and from unverified internal wiki."],
        counterarguments=[],
        target_result=dummy_res,
    )
    assert cat == DisagreementType.EVIDENCE

    # 4. FACTUAL
    cat = detector._classify_disagreement_nature(
        issues=["Benchmark measured throughput contradicted by verified hardware telemetry."],
        counterarguments=[],
        target_result=dummy_res,
    )
    assert cat == DisagreementType.FACTUAL

    # 5. TEMPORAL
    cat = detector._classify_disagreement_nature(
        issues=["Timeout thresholds for socket lease renewal expire prematurely."],
        counterarguments=[],
        target_result=dummy_res,
    )
    assert cat == DisagreementType.TEMPORAL

    # 6. SCOPE
    cat = detector._classify_disagreement_nature(
        issues=["Security boundary does not apply across VPC limits."],
        counterarguments=[],
        target_result=dummy_res,
    )
    assert cat == DisagreementType.SCOPE

    # 7. MODEL
    cat = detector._classify_disagreement_nature(
        issues=["Monte Carlo simulation model failed to represent tail packet drop."],
        counterarguments=[],
        target_result=dummy_res,
    )
    assert cat == DisagreementType.MODEL

    # 8. OBJECTIVE
    cat = detector._classify_disagreement_nature(
        issues=["Conflicting priority between cost minimization and maximum throughput."],
        counterarguments=[],
        target_result=dummy_res,
    )
    assert cat == DisagreementType.OBJECTIVE

    # 9. INTERPRETATION
    cat = detector._classify_disagreement_nature(
        issues=["Divergent interpretation of SLA latency percentiles."],
        counterarguments=[],
        target_result=dummy_res,
    )
    assert cat == DisagreementType.INTERPRETATION

    # 10. PREFERENCE
    cat = detector._classify_disagreement_nature(
        issues=["Subjective stylistic pattern difference."],
        counterarguments=[],
        target_result=dummy_res,
    )
    assert cat == DisagreementType.PREFERENCE


def test_cross_result_contradiction_detection():
    detector = DisagreementDetector()

    r1 = AgentResult(
        agent_id="agt_arch",
        task_id="tsk_1",
        role="ARCHITECT",
        answer="Event pipeline scales throughput up to 50k QPS without degradation.",
    )
    r2 = AgentResult(
        agent_id="agt_perf",
        task_id="tsk_2",
        role="OPTIMIZER",
        answer="Event pipeline introduces severe bottleneck at consumer deserialization stage.",
    )

    disagreements = detector.detect_disagreements(
        results=[r1, r2],
        reviews=[],
    )

    assert len(disagreements) >= 1
    assert any(
        "agt_arch" in d.involved_agent_ids and "agt_perf" in d.involved_agent_ids for d in disagreements
    )


def test_controlled_debate_engine_execution_and_hard_round_cap():
    engine = DebateEngine()

    a1 = SwarmAgentSpec(
        agent_id="agt_arch_01",
        name="Architect",
        role="ARCHITECT",
        capabilities=["architecture"],
        limitations=["no production edit"],
    )
    a2 = SwarmAgentSpec(
        agent_id="agt_critic_01",
        name="Critic",
        role="CRITIC",
        capabilities=["red_team"],
        limitations=["no mutation"],
    )

    disagreement = DisagreementRecord(
        category=DisagreementType.CAUSAL,
        issue="Message bus replication latency impact",
        involved_agent_ids=["agt_arch_01", "agt_critic_01"],
        positions={
            "agt_arch_01": "In-memory replication keeps latency under 5ms.",
            "agt_critic_01": "Disk sync under network partition causes stalls.",
        },
    )

    # Requesting 10 rounds must be capped at 3 by the safety invariant
    session = engine.orchestrate_debate(
        topic="Replication Latency & Partition Resilience",
        disagreement=disagreement,
        agents=[a1, a2],
        max_rounds=10,
    )

    assert session.max_rounds == 3  # Hard safety cap
    assert session.status in [
        DebateStatus.CONCLUDED,
        DebateStatus.CONVERGED,
        DebateStatus.RESOLVED,
        DebateStatus.IN_PROGRESS,
    ]

    # Verify structured dialectical progression
    for rnd in session.rounds:
        assert len(rnd.turns) >= 2
        for turn in rnd.turns:
            assert turn.statement != ""
            assert turn.agent_id in ["agt_arch_01", "agt_critic_01"]
