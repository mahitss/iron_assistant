import pytest
from fastapi.testclient import TestClient
from app.main import create_app
from app.prediction.service import PredictionService
from app.prediction.forecasts import PredictionWindow
from app.prediction.early_warning import WarningSeverity


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


def test_prediction_service_full_workflow():
    service = PredictionService()

    # 1. Generate prediction
    pred = service.generate_prediction(
        subject="service:payment_processor",
        event="connection_timeout_spike",
        predicted_state={"timeout_rate_pct": 15},
        prediction_window=PredictionWindow.NEAR_TERM,
        confidence=0.80,
        evidence_refs=["metric:timeout_rate:5%"],
        user_id="user_admin",
        project_id="proj_core",
    )
    assert pred.prediction_id.startswith("pred_")

    # 2. Explanation
    explanation = service.explain_prediction(pred.prediction_id)
    assert "payment_processor" in explanation
    assert "CONFIDENCE" in explanation or "Confidence" in explanation

    # 3. Multi-agent review
    review = service.review_prediction(
        prediction_id=pred.prediction_id,
        reviewer_agent_id="agent_supervisor",
        assessment="EVIDENCE_VALID",
        critique="Evidence confirms consistent upward slope across 3 nodes",
    )
    assert review.reviewer_agent_id == "agent_supervisor"
    assert review.assessment == "EVIDENCE_VALID"

    # 4. Dependency cascade analysis
    cascade = service.anticipate_cascade_risk(
        root_service="service:payment_processor",
        event="service_unavailable",
        downstream_services=["service:checkout", "service:billing"],
        probability=0.75,
    )
    assert cascade.root_service == "service:payment_processor"
    assert len(cascade.affected_services) == 2


def test_prediction_api_endpoints(client):
    headers = {"X-User-Id": "user_test", "X-Project-Id": "proj_test"}

    # 1. Create prediction
    res = client.post(
        "/api/v1/prediction/predictions",
        headers=headers,
        json={
            "subject": "service:inventory",
            "event": "stock_sync_delay",
            "predicted_state": {"sync_lag_seconds": 120},
            "prediction_window": "near-term",
            "confidence": 0.85,
            "evidence_refs": ["queue_depth_increasing"],
            "assumptions": ["network bandwidth unchanged"],
        },
    )
    assert res.status_code in [200, 201], res.text
    data = res.json()
    assert "prediction_id" in data
    pred_id = data["prediction_id"]

    # 2. List predictions
    res_list = client.get("/api/v1/prediction/predictions", headers=headers)
    assert res_list.status_code == 200
    assert len(res_list.json()) >= 1

    # 3. Create Early Warning
    res_warn = client.post(
        "/api/v1/prediction/warnings",
        headers=headers,
        json={
            "target": "redis:cluster",
            "signal": "eviction_rate_high",
            "predicted_event": "cache_thrashing",
            "timeframe": "near-term",
            "confidence": 0.80,
            "severity": "HIGH",
            "evidence": ["evicted_keys_per_sec:1200"],
        },
    )
    assert res_warn.status_code in [200, 201]
    warn_data = res_warn.json()
    assert warn_data["severity"] == "HIGH"

    # 4. List Warnings
    res_warn_list = client.get("/api/v1/prediction/warnings", headers=headers)
    assert res_warn_list.status_code == 200

    # 5. Run Scenario Simulation
    res_sim = client.post(
        "/api/v1/prediction/simulation",
        headers=headers,
        json={
            "scenario_name": "black_friday_load",
            "initial_state": {"rps": 5000},
            "steps": 4,
            "interventions": [{"step": 2, "action": "enable_rate_limiting"}],
        },
    )
    assert res_sim.status_code == 200
    sim_data = res_sim.json()
    assert sim_data["label"] == "SIMULATED"
    assert sim_data["is_simulated"] is True

    # 6. Counterfactual
    res_cf = client.post(
        "/api/v1/prediction/counterfactual",
        headers=headers,
        json={
            "subject": "service:orders",
            "current_trend": "increasing_error_rate",
            "proposed_action": "rollback_last_commit",
            "horizon_hours": 12,
        },
    )
    assert res_cf.status_code == 200
    cf_data = res_cf.json()
    assert cf_data["label"] == "HYPOTHETICAL"
    assert cf_data["is_hypothetical"] is True

    # 7. Calibration Metrics
    res_calib = client.get("/api/v1/prediction/calibration", headers=headers)
    assert res_calib.status_code == 200
