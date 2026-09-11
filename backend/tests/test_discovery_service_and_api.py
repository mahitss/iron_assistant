"""Integration tests for DiscoveryEngineService and REST API (Task 72)."""

import pytest
from fastapi.testclient import TestClient

from app.discovery.schemas import (
    AnalysisOutcome,
    DiscoveryRequest,
    DiscoveryState,
    EnvironmentType,
    ExperimentStatus,
    ExperimentType,
    RiskLevel,
    RollbackPlan,
)
from app.discovery.service import DiscoveryEngineService
from app.main import create_app


@pytest.fixture(autouse=True)
def reset_discovery_singleton():
    """Reset service singleton before each test for total isolation."""
    DiscoveryEngineService.reset_instance()
    yield
    DiscoveryEngineService.reset_instance()


def test_discovery_service_end_to_end_lifecycle():
    """Verifies complete scientific loop:

    QUESTION -> HYPOTHESES -> EXPERIMENT DESIGN -> PREDICTION -> EXECUTION -> OBSERVATION -> RESULT -> CONCLUSION -> KNOWLEDGE
    """
    service = DiscoveryEngineService.get_instance()

    # 1. Start discovery
    req = DiscoveryRequest(
        question="Did configuration change X increase production latency?",
        objective="Determine if config X caused p95 latency regression",
        domain="infrastructure",
        initial_hypotheses=["Config timeout parameter caused worker thread starvation"],
    )
    session = service.start_discovery(req)

    assert session.discovery_id.startswith("dsc-")
    assert session.status in {DiscoveryState.QUESTION_FORMED, DiscoveryState.HYPOTHESIS_GENERATED}
    assert len(session.questions) == 1
    assert len(session.hypotheses) >= 1
    h_id = session.hypotheses[0].hypothesis_id

    # 2. Design safe trial in staging
    exp = service.design_experiment(
        discovery_id=session.discovery_id,
        hypothesis_ids=[h_id],
        objective="Test worker timeout adjustment in staging cluster",
        experiment_type=ExperimentType.OBSERVATIONAL,
        environment=EnvironmentType.STAGING,
        dependent_variables=["p95_latency_ms"],
        expected_information_gain=0.85,
    )
    assert exp.status == ExperimentStatus.READY
    assert exp.risk_level == RiskLevel.LOW_RISK

    # 3. Record immutable pre-execution prediction
    pred = service.record_pre_execution_prediction(
        experiment_id=exp.experiment_id,
        hypothesis_id=h_id,
        expected_direction="decrease",
        confidence=0.80,
    )
    assert pred.is_immutable is True

    # 4. Execute experiment safely
    result = service.execute_safe_experiment(
        experiment_id=exp.experiment_id,
        mock_observation_value={"delta": -0.25},
    )
    assert result.outcome == AnalysisOutcome.SUPPORTED
    assert result.is_valid is True

    # Target hypothesis confidence should increase
    updated_h = next(h for h in session.hypotheses if h.hypothesis_id == h_id)
    assert updated_h.confidence > 0.5
    assert updated_h.status == "SUPPORTED"

    # 5. Conclude discovery & update knowledge
    concluded = service.conclude_discovery(session.discovery_id)
    assert concluded.status == DiscoveryState.COMPLETED
    assert len(concluded.conclusions) > 0
    assert concluded.completed_at is not None

    # Audit events recorded
    audits = service.get_audit_trail(discovery_id=session.discovery_id)
    event_types = [a.event_type for a in audits]
    assert "DISCOVERY_CREATED" in event_types
    assert "EXPERIMENT_DESIGNED" in event_types
    assert "PREDICTION_RECORDED" in event_types
    assert "EXPERIMENT_STARTED" in event_types
    assert "HYPOTHESIS_SUPPORTED" in event_types
    assert "KNOWLEDGE_CANDIDATE_CREATED" in event_types
    assert "DISCOVERY_COMPLETED" in event_types


def test_experiment_queue_dependencies_and_approvals():
    """Verifies dependency resolution (A -> B) and approval gating for high risk experiments."""
    service = DiscoveryEngineService.get_instance()

    session = service.start_discovery(
        DiscoveryRequest(question="Will database index rebuild optimize join latency?")
    )

    # Exp A: Safe preparatory trial
    exp_a = service.design_experiment(
        discovery_id=session.discovery_id,
        hypothesis_ids=["hyp_idx"],
        objective="Simulate index query plan",
        experiment_type=ExperimentType.SIMULATION,
        environment=EnvironmentType.SIMULATION,
    )
    # Exp B: High risk trial in Staging that depends on Exp A
    exp_b = service.design_experiment(
        discovery_id=session.discovery_id,
        hypothesis_ids=["hyp_idx"],
        objective="Apply index concurrently in staging",
        experiment_type=ExperimentType.CONTROLLED,
        environment=EnvironmentType.STAGING,
        dependencies=[exp_a.experiment_id],
        rollback_plan=RollbackPlan(rollback_action="drop_index_idx_test"),
    )

    # Exp B is blocked until Exp A completes
    assert exp_b.status == ExperimentStatus.BLOCKED

    # Run Exp A
    service.record_pre_execution_prediction(
        experiment_id=exp_a.experiment_id,
        hypothesis_id="hyp_idx",
        expected_direction="decrease",
    )
    service.execute_safe_experiment(exp_a.experiment_id, mock_observation_value={"delta": -0.30})

    # Now Exp A is completed. Exp B requires approval because Staging mutable is MEDIUM_RISK / auth_required
    assert exp_b.status == ExperimentStatus.APPROVAL_REQUIRED

    # Attempting to run unapproved experiment must raise PermissionError
    service.record_pre_execution_prediction(
        experiment_id=exp_b.experiment_id,
        hypothesis_id="hyp_idx",
        expected_direction="decrease",
    )
    with pytest.raises(PermissionError, match="requires explicit human approval"):
        service.execute_safe_experiment(exp_b.experiment_id)

    # Grant human approval
    service.approve_experiment(exp_b.experiment_id, approver="Principal Engineer")
    assert exp_b.is_authorized is True
    assert exp_b.status == ExperimentStatus.READY

    # Now executes safely
    res_b = service.execute_safe_experiment(exp_b.experiment_id, mock_observation_value={"delta": -0.40})
    assert res_b.is_valid is True


def test_unexpected_anomaly_generates_new_hypothesis():
    """Detecting an unexpected outcome generates an anomaly and candidate explanation."""
    service = DiscoveryEngineService.get_instance()

    session = service.start_discovery(
        DiscoveryRequest(
            question="Why does enabling cache compression impact CPU?",
            initial_hypotheses=["Compression will reduce memory pressure with negligible latency delta"],
        )
    )
    h_id = session.hypotheses[0].hypothesis_id

    exp = service.design_experiment(
        discovery_id=session.discovery_id,
        hypothesis_ids=[h_id],
        objective="Measure memory footprint under zstd compression",
        experiment_type=ExperimentType.OBSERVATIONAL,
        environment=EnvironmentType.STAGING,
    )
    service.record_pre_execution_prediction(
        experiment_id=exp.experiment_id,
        hypothesis_id=h_id,
        expected_direction="decrease",
    )

    # Opposite effect observed (+0.95 increase in latency / CPU load)
    result = service.execute_safe_experiment(
        experiment_id=exp.experiment_id,
        mock_observation_value={"delta": +0.95},
    )

    assert result.outcome == AnalysisOutcome.UNEXPECTED
    assert result.unexpected_anomaly_detected is True
    # New hypothesis dynamically generated in session
    assert len(session.hypotheses) > 1
    assert any("unexpected" in h.source or "counter-mechanism" in h.description for h in session.hypotheses)


def test_rollback_and_cleanup_operations():
    """Verifies safe rollback and cleanup execution with complete provenance."""
    service = DiscoveryEngineService.get_instance()

    session = service.start_discovery(DiscoveryRequest(question="Test rollback mechanics"))
    exp = service.design_experiment(
        discovery_id=session.discovery_id,
        hypothesis_ids=["h_test"],
        objective="Config change with rollback",
        experiment_type=ExperimentType.CONTROLLED,
        environment=EnvironmentType.STAGING,
        rollback_plan=RollbackPlan(rollback_action="revert_sysctl_tcp_fastopen"),
    )

    rb_res = service.rollback_experiment(exp.experiment_id, actor="OpsAgent")
    assert rb_res["status"] == "ROLLED_BACK"
    assert rb_res["rollback_action"] == "revert_sysctl_tcp_fastopen"

    cl_res = service.cleanup_experiment(exp.experiment_id)
    assert cl_res["status"] == "CLEANED_UP"


def test_discovery_rest_api():
    """Verifies FastAPI endpoints for Discovery and Experiments."""
    app = create_app()
    client = TestClient(app)

    # 1. Start discovery
    resp = client.post(
        "/api/v1/discovery/start",
        json={
            "question": "Does increasing pool size improve response time?",
            "objective": "Empirical evaluation of connection pool depth",
            "domain": "performance",
        },
        headers={"X-Tenant-ID": "test_tenant", "X-Workspace-ID": "test_ws"},
    )
    assert resp.status_code == 201
    disc_data = resp.json()
    disc_id = disc_data["discovery_id"]
    assert disc_id.startswith("dsc-")

    # 2. Get discovery
    resp = client.get(f"/api/v1/discovery/{disc_id}")
    assert resp.status_code == 200
    assert resp.json()["question"] == "Does increasing pool size improve response time?"

    # 3. Add hypotheses
    resp = client.post(
        f"/api/v1/discovery/{disc_id}/hypotheses",
        json={
            "candidate_explanations": [
                {
                    "description": "Pool contention caused wait queues",
                    "falsification_criteria": ["Wait queue length remains zero"],
                    "plausibility": 0.8,
                }
            ]
        },
    )
    assert resp.status_code == 200
    hyps = resp.json()
    assert len(hyps) >= 1
    hyp_id = hyps[0]["hypothesis_id"]

    # 4. Design experiment
    resp = client.post(
        "/api/v1/experiments/design",
        json={
            "discovery_id": disc_id,
            "hypothesis_ids": [hyp_id],
            "objective": "Observe wait queues under steady traffic",
            "experiment_type": "OBSERVATIONAL",
            "environment": "STAGING",
        },
    )
    assert resp.status_code == 201
    exp_data = resp.json()
    exp_id = exp_data["experiment_id"]

    # 5. Record prediction
    resp = client.post(
        f"/api/v1/experiments/{exp_id}/prediction",
        json={
            "hypothesis_id": hyp_id,
            "expected_direction": "decrease",
            "confidence": 0.75,
        },
    )
    assert resp.status_code == 200
    assert resp.json()["expected_direction"] == "decrease"

    # 6. Start experiment
    resp = client.post(
        f"/api/v1/experiments/{exp_id}/start",
        json={"mock_observation_value": {"delta": -0.18}},
    )
    assert resp.status_code == 200
    res_data = resp.json()
    assert res_data["outcome"] == "SUPPORTED"

    # 7. Get explanation
    resp = client.get(f"/api/v1/experiments/{exp_id}/explanation")
    assert resp.status_code == 200
    assert "rationale" in resp.json()

    # 8. Queue & Health
    resp = client.get("/api/v1/experiments/queue")
    assert resp.status_code == 200
    assert "status_counts" in resp.json()

    resp = client.get("/api/v1/experiments/health")
    assert resp.status_code == 200
    assert "active_discoveries" in resp.json()
