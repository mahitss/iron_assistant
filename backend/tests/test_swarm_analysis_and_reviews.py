"""Unit tests for Independent Analysis, Epistemic Claims, Lineage Grouping, and Peer Reviews (Task 64)."""

from app.swarm.analysis import IndependentAnalysisCoordinator
from app.swarm.review import PeerReviewEngine
from app.swarm.schemas import (
    CollectiveObjective,
    EpistemicType,
    SwarmAgentSpec,
    SwarmTaskNode,
)


def test_independent_analysis_epistemic_classification():
    coordinator = IndependentAnalysisCoordinator()
    objective = CollectiveObjective(
        goal="Design resilient caching layer for tenant metadata",
        risk_level="HIGH",
    )
    task = SwarmTaskNode(
        title="Architectural evaluation",
        description="Evaluate caching layer",
        role_needed="ARCHITECT",
    )
    agent = SwarmAgentSpec(
        agent_id="swm_agt_architect_01",
        name="Architect Agent",
        role="ARCHITECT",
        capabilities=["architecture_design"],
        limitations=["no production rollout"],
    )

    result = coordinator.execute_independent_analysis(task, agent, objective)

    assert result.agent_id == agent.agent_id
    assert result.role == "ARCHITECT"
    assert len(result.claims) > 0

    # Epistemic classification check: CLAIM != EVIDENCE != ASSUMPTION
    claim = result.claims[0]
    assert claim.epistemic_type in [
        EpistemicType.CLAIM,
        EpistemicType.INFERENCE,
        EpistemicType.RECOMMENDATION,
    ]
    assert len(result.evidence) > 0
    assert len(result.assumptions) > 0
    assert len(result.uncertainties) > 0


def test_evidence_lineage_grouping_invariant():
    coordinator = IndependentAnalysisCoordinator()
    objective = CollectiveObjective(
        goal="Verify throughput benchmarks for storage cluster",
        risk_level="MEDIUM",
    )

    # 3 agents all reading the same benchmark report
    t1 = SwarmTaskNode(title="T1", description="desc", role_needed="RESEARCHER")
    t2 = SwarmTaskNode(title="T2", description="desc", role_needed="RESEARCHER")
    t3 = SwarmTaskNode(title="T3", description="desc", role_needed="RESEARCHER")

    a1 = SwarmAgentSpec(agent_id="agt_1", name="A1", role="RESEARCHER")
    a2 = SwarmAgentSpec(agent_id="agt_2", name="A2", role="RESEARCHER")
    a3 = SwarmAgentSpec(agent_id="agt_3", name="A3", role="RESEARCHER")

    r1 = coordinator.execute_independent_analysis(t1, a1, objective)
    r2 = coordinator.execute_independent_analysis(t2, a2, objective)
    r3 = coordinator.execute_independent_analysis(t3, a3, objective)

    # Invariant: Multiple agents citing the same source is 1 lineage group, NOT 3 independent confirmations
    lineage_groups = coordinator.compute_evidence_lineage_groups([r1, r2, r3])

    root_id = "src_distributed_consensus_paper"
    assert root_id in lineage_groups
    assert len(lineage_groups[root_id]) == 3


def test_blind_peer_review_generation():
    coordinator = IndependentAnalysisCoordinator()
    review_engine = PeerReviewEngine()

    objective = CollectiveObjective(
        goal="Audit container network policy",
        risk_level="HIGH",
    )
    t_arch = SwarmTaskNode(title="Arch", description="Arch", role_needed="ARCHITECT")
    a_arch = SwarmAgentSpec(agent_id="agt_arch", name="Architect", role="ARCHITECT")
    target_result = coordinator.execute_independent_analysis(t_arch, a_arch, objective)

    # Blind review by Critic
    a_critic = SwarmAgentSpec(agent_id="agt_critic", name="Critic", role="CRITIC")
    review = review_engine.conduct_peer_review(
        reviewer=a_critic,
        target_result=target_result,
        is_blind=True,
    )

    assert review.reviewer_agent_id == a_critic.agent_id
    assert review.target_result_id == target_result.result_id
    assert review.is_blind is True
    assert len(review.counterarguments) > 0
    assert review.recommendation in ["ENDORSE", "QUALIFIED_ENDORSE", "CHALLENGE"]


def test_peer_review_penalizes_unsupported_assertions():
    coordinator = IndependentAnalysisCoordinator()
    review_engine = PeerReviewEngine()

    objective = CollectiveObjective(goal="Evaluate arbitrary tool", risk_level="LOW")
    t = SwarmTaskNode(title="T", description="D", role_needed="ANALYST")
    a = SwarmAgentSpec(agent_id="agt_basic", name="Basic", role="ANALYST")
    res = coordinator.execute_independent_analysis(t, a, objective)

    # Strip evidence to simulate unsupported assertion
    res.evidence = []

    a_critic = SwarmAgentSpec(agent_id="agt_critic", name="Critic", role="CRITIC")
    review = review_engine.conduct_peer_review(reviewer=a_critic, target_result=res)

    assert any("sparse cited empirical evidence" in issue for issue in review.issues)
    assert review.correctness_score <= 0.70
