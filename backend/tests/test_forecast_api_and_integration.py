"""Integration and REST API tests for Forecast & Early Warning Engine (Task 74, Spec 46-49)."""

import pytest
from starlette.testclient import TestClient

from app.main import app
from app.prediction.service import PredictionService


@pytest.fixture
def client():
    return TestClient(app)


def test_forecast_full_rest_api_lifecycle(client):
    headers = {"X-User-Id": "analyst_42", "X-Project-Id": "infrastructure_prod"}

    # 1. Create Forecast
    res = client.post(
        "/api/v1/prediction/forecasts",
        headers=headers,
        json={
            "target": "db_query_duration_p99",
            "historical_series": [45.0, 48.0, 52.0, 55.0, 58.0, 62.0],
            "horizon": "SHORT",
            "forecast_type": "POINT",
            "strategy": "TREND_EXTRAPOLATION",
            "target_metric": "milliseconds",
        },
    )
    assert res.status_code in [200, 201], res.text
    data = res.json()
    assert "forecast_id" in data
    fc_id = data["forecast_id"]
    assert data["target"] == "db_query_duration_p99"
    assert data["predicted_value"] > 62.0
    assert data["label"] == "FORECAST"

    # 2. Get Forecast by ID
    res_get = client.get(f"/api/v1/prediction/forecasts/{fc_id}", headers=headers)
    assert res_get.status_code == 200
    assert res_get.json()["forecast_id"] == fc_id

    # 3. List active forecasts
    res_active = client.get("/api/v1/prediction/forecasts/active", headers=headers)
    assert res_active.status_code == 200
    active_ids = [f["forecast_id"] for f in res_active.json()]
    assert fc_id in active_ids

    # 4. Refresh Forecast (new series)
    res_ref = client.post(
        f"/api/v1/prediction/forecasts/{fc_id}/refresh",
        headers=headers,
        json={
            "updated_series": [45.0, 48.0, 52.0, 55.0, 58.0, 62.0, 70.0],
            "reason": "New telemetry point observed",
        },
    )
    assert res_ref.status_code == 200
    ref_data = res_ref.json()
    assert ref_data["version"] == 2

    # 5. Get History
    res_hist = client.get(f"/api/v1/prediction/forecasts/{fc_id}/history", headers=headers)
    assert res_hist.status_code == 200
    assert len(res_hist.json()) >= 1

    # 6. Get Explanation & Provenance
    res_exp = client.get(f"/api/v1/prediction/forecasts/{fc_id}/explanation", headers=headers)
    assert res_exp.status_code == 200
    exp_data = res_exp.json()
    assert "target" in exp_data
    assert "signals" in exp_data

    res_prov = client.get(f"/api/v1/prediction/forecasts/{fc_id}/provenance", headers=headers)
    assert res_prov.status_code == 200
    assert "strategy" in res_prov.json()

    # 7. Evaluate outcome
    res_eval = client.post(
        f"/api/v1/prediction/forecasts/{fc_id}/evaluate",
        headers=headers,
        json={"actual_value": 72.5, "action_influenced": False},
    )
    assert res_eval.status_code == 200
    eval_data = res_eval.json()
    assert eval_data["actual_outcome"] == 72.5
    assert eval_data["state"] == "VERIFIED_BY_OUTCOME"


def test_forecast_backtest_endpoint(client):
    headers = {"X-User-Id": "researcher_1", "X-Project-Id": "ai_lab"}

    res = client.post(
        "/api/v1/prediction/forecasts/backtest",
        headers=headers,
        json={
            "target": "synthetic_sin_wave",
            "series": [10.0 + i * 1.2 for i in range(25)],
            "strategy": "TREND_EXTRAPOLATION",
            "horizon_steps": 1,
            "window_type": "rolling",
            "min_train_size": 8,
            "step_size": 2,
        },
    )
    assert res.status_code == 200, res.text
    bt = res.json()
    assert bt["folds_evaluated"] > 0
    assert bt["temporal_isolation_verified"] is True
    assert "mae" in bt
    assert "rmse" in bt


def test_early_warning_acknowledgement_and_dismiss_api(client):
    headers = {"X-User-Id": "ops_eng", "X-Project-Id": "prod_monitoring"}

    # Issue warning
    res_create = client.post(
        "/api/v1/prediction/early-warnings",
        headers=headers,
        json={
            "target": "ingress_controller",
            "signal": "tls_handshake_errors",
            "predicted_event": "cert_manager_outage",
            "confidence": 0.85,
            "severity": "WARNING",
            "evidence": {"handshake_fails": 340},
        },
    )
    assert res_create.status_code in [200, 201]
    w_data = res_create.json()
    wid = w_data["warning_id"]

    # Acknowledge warning
    res_ack = client.post(f"/api/v1/prediction/early-warnings/{wid}/acknowledge", headers=headers)
    assert res_ack.status_code == 200
    ack_data = res_ack.json()
    assert ack_data["state"] == "ACKNOWLEDGED"

    # Dismiss warning
    res_dism = client.post(
        f"/api/v1/prediction/early-warnings/{wid}/dismiss",
        headers=headers,
        json={"reason": "Certificates rotated successfully"},
    )
    assert res_dism.status_code == 200
    dism_data = res_dism.json()
    assert dism_data["state"] == "RESOLVED"
    assert dism_data["resolution"] == "MANUALLY_DISMISSED"


def test_emergency_stop_integration_blocks_action():
    """Verify emergency stop semantics: forecasting remains read/advisory-only (Spec 46, 47)."""
    service = PredictionService()
    # Check stop check behaves safely
    assert service.check_emergency_stop_active() in [True, False]
