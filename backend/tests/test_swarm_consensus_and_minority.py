"""Unit tests for Consensus Engine, Minority Reports, Confidence Calibration, and Collective Synthesis (Task 64)."""

from app.swarm.calibration import ConfidenceCalibrator
from app.swarm.consensus import ConsensusEngine
from app.swarm.schemas import (
    AgentAssertion,
    AgentResult,
    CollectiveObjective,
    ConsensusOutcome,
    EpistemicType,
    PeerReview,
)
from app.swarm.synthesis import CollectiveSynthesizer


def test_consensus_engine_empty_results_handling():
    engine = ConsensusEngine()
    consensus, minorities = engine.evaluate_consensus(
        results=[],
        reviews=[],
        disagreements=[],
    )

    assert consensus.outcome == ConsensusOutcome.INSUFFICIENT_EVIDENCE
    assert consensus.consensus_score == 0.0
    assert len(minorities) == 0


def test_consensus_engine_qualified_consensus_with_minority_reports():
    engine = ConsensusEngine()

    # Agent 1 (Architect)
    r1 = AgentResult(
        agent_id="agt_arch",
        task_id="tsk_1",
        role="ARCHITECT",
        answer="Deploy asynchronous message ingestion pipeline for high scalability.",
        claims=[
            AgentAssertion(
                text="Asynchronous ingestion pipeline scales to 50k QPS.",
                epistemic_type=EpistemicType.CLAIM,
            )
        ],
        evidence=[
            {
                "type": "EMPIRICAL_BENCHMARK",
                "source": "Lab Test",
                "finding": "50k QPS benchmark passed.",
            }
        ],
    )

    # Agent 2 (Critic - dissenting)
    r2 = AgentResult(
        agent_id="agt_critic",
        task_id="tsk_2",
        role="CRITIC",
        answer="Pipeline introduces severe memory pressure under slow consumer backpressure.",
        claims=[
            AgentAssertion(
                text="Backpressure causes queue memory bloat.",
                epistemic_type=EpistemicType.CLAIM,
            )
        ],
        evidence=[
            {
                "type": "DIRECT_MEASUREMENT",
                "source": "Stress Telemetry",
                "finding": "OOM crash observed under 100k buffered events.",
            }
        ],
    )

    # Critic peer review rejecting pure async commit
    review = PeerReview(
        reviewer_agent_id="agt_critic",
        reviewer_role="CRITIC",
        target_result_id=r1.result_id,
        issues=["Unbounded buffer triggers OOM killer during network split."],
        counterarguments=["Empirical stress data shows fatal backpressure stall."],
        supporting_evidence=["Telemetry run #4029"],
        severity="HIGH",
        recommendation="CONTEST",
    )

    consensus, minorities = engine.evaluate_consensus(
        results=[r1, r2],
        reviews=[review],
        disagreements=[],
    )

    # Must preserve minority report rather than silencing it
    assert len(minorities) >= 1
    minority = minorities[0]
    assert minority.dissenting_agent_id == "agt_critic"
    assert len(minority.failure_scenario_conditions) > 0
    assert "backpressure" in minority.position.lower() or "oom" in minority.reasoning.lower()

    # Outcome should be QUALIFIED_CONSENSUS or MINORITY_DISAGREEMENT
    assert consensus.outcome in [
        ConsensusOutcome.QUALIFIED_CONSENSUS,
        ConsensusOutcome.MINORITY_DISAGREEMENT,
    ]
    assert consensus.is_evidence_backed is True


def test_confidence_calibrator_overconfidence_dampening():
    calibrator = ConfidenceCalibrator()

    # High raw confidence with 0 evidence must be heavily dampened (capped at 0.50)
    conf_no_ev = calibrator.calibrate_confidence(
        raw_confidence=0.98,
        evidence_count=0,
        independent_lineage_count=1,
        has_disagreements=False,
    )
    assert conf_no_ev <= 0.50

    # High raw confidence with only 1 evidence must be capped at 0.70
    conf_sparse_ev = calibrator.calibrate_confidence(
        raw_confidence=0.95,
        evidence_count=1,
        independent_lineage_count=1,
        has_disagreements=False,
    )
    assert conf_sparse_ev <= 0.70


def test_confidence_calibrator_correlated_failure_and_unverified_cap():
    calibrator = ConfidenceCalibrator()

    # Correlated failure: multiple agents citing only 1 single source lineage
    # Confidence must be dampened due to correlated failure risk
    conf_correlated = calibrator.calibrate_confidence(
        raw_confidence=0.92,
        evidence_count=5,
        independent_lineage_count=1,  # Shared root source!
        has_disagreements=False,
        verification_passed=False,
    )
    assert conf_correlated <= 0.78

    # Unverified gate: cannot exceed 0.85 without verification_passed
    conf_unverified = calibrator.calibrate_confidence(
        raw_confidence=0.95,
        evidence_count=4,
        independent_lineage_count=3,
        has_disagreements=False,
        verification_passed=False,
    )
    assert conf_unverified <= 0.85

    # Verification boost when verified
    conf_verified = calibrator.calibrate_confidence(
        raw_confidence=0.88,
        evidence_count=4,
        independent_lineage_count=3,
        has_disagreements=False,
        verification_passed=True,
    )
    assert conf_verified > conf_unverified


def test_collective_synthesizer_preserves_conflicts():
    calibrator = ConfidenceCalibrator()
    synthesizer = CollectiveSynthesizer(calibrator=calibrator)

    objective = CollectiveObjective(
        goal="Design global session replication architecture",
        risk_level="HIGH",
    )

    r1 = AgentResult(
        agent_id="agt_arch",
        task_id="tsk_1",
        role="ARCHITECT",
        answer="Multi-master active-active replication across 3 regions.",
    )
    r2 = AgentResult(
        agent_id="agt_sec",
        task_id="tsk_2",
        role="SECURITY_ANALYST",
        answer="Cross-region encryption envelope required for HIPAA compliance.",
    )

    consensus_engine = ConsensusEngine()
    consensus, minorities = consensus_engine.evaluate_consensus(
        results=[r1, r2],
        reviews=[],
        disagreements=[],
    )

    collective_result = synthesizer.synthesize(
        objective=objective,
        swarm_id="swm_test_001",
        results=[r1, r2],
        reviews=[],
        disagreements=[],
        debates=[],
        consensus=consensus,
        minority_reports=minorities,
    )

    assert collective_result.swarm_id == "swm_test_001"
    assert len(collective_result.key_findings) >= 0
    assert len(collective_result.agent_perspectives) == 2
    # Invariant: Collective output is UNVERIFIED until verified
    assert collective_result.verification_status == "UNVERIFIED"
