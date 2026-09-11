"""Integration tests for propagation REST API endpoints and CLI parser (Spec 63, 79)."""

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.propagation.cli import build_parser, main


@pytest.fixture(scope="module")
def client():
    app = create_app()
    with TestClient(app) as tc:
        yield tc


def test_api_propagation_analyze_and_inspect_flow(client: TestClient):
    """Verify POST /propagation/analyze and subsequent inspection endpoints (Spec 63)."""
    payload = {
        "origin_entity": "auth_service",
        "trigger": "Auth token cache connection drop",
        "trigger_type": "FAILURE",
        "scope": "SERVICE",
        "custom_edges": [
            {
                "source_entity": "auth_service",
                "target_entity": "api_gateway",
                "relationship_type": "DEPENDS_ON",
                "confidence": 0.9,
            },
            {
                "source_entity": "api_gateway",
                "target_entity": "user_dashboard",
                "relationship_type": "DEPENDS_ON",
                "confidence": 0.85,
            },
        ],
    }

    # 1. Analyze endpoint
    res_analyze = client.post("/propagation/analyze", json=payload)
    assert res_analyze.status_code == 201
    data = res_analyze.json()
    assert "propagation_id" in data
    prop_id = data["propagation_id"]
    assert data["origin_entity"] == "auth_service"
    assert len(data["direct_effects"]) >= 1

    # 2. Get Analysis by ID
    res_get = client.get(f"/propagation/{prop_id}")
    assert res_get.status_code == 200
    assert res_get.json()["propagation_id"] == prop_id

    # 3. Graph endpoint
    res_graph = client.get(f"/propagation/{prop_id}/graph")
    assert res_graph.status_code == 200
    assert "nodes" in res_graph.json()
    assert "edges" in res_graph.json()

    # 4. Explanation endpoint
    res_exp = client.get(f"/propagation/{prop_id}/explanation")
    assert res_exp.status_code == 200
    assert "steps" in res_exp.json()

    # 5. Provenance endpoint
    res_prov = client.get(f"/propagation/{prop_id}/provenance")
    assert res_prov.status_code == 200
    assert "graph_snapshot" in res_prov.json()

    # 6. Scenarios endpoint
    res_scen = client.get(f"/propagation/{prop_id}/scenarios?intervention_type=ADD_REDUNDANCY")
    assert res_scen.status_code == 200
    assert "counterfactual_result" in res_scen.json()

    # 7. Outcome evaluation endpoint
    res_out = client.post(
        f"/propagation/{prop_id}/outcome",
        json={"actual_degraded_nodes": ["api_gateway", "user_dashboard"]},
    )
    assert res_out.status_code == 200
    assert res_out.json()["node_precision"] > 0.0


def test_api_active_cascades_and_resilience_queries(client: TestClient):
    """Verify GET /propagation/active, /bottlenecks, /single-points-of-failure, and /resilience (Spec 63)."""
    # Active cascades
    res_casc = client.get("/propagation/active")
    assert res_casc.status_code == 200
    assert isinstance(res_casc.json(), list)

    # Cascades alias
    res_alias = client.get("/propagation/cascades")
    assert res_alias.status_code == 200
    assert isinstance(res_alias.json(), list)

    # Bottlenecks
    res_bot = client.get("/propagation/bottlenecks")
    assert res_bot.status_code == 200
    assert isinstance(res_bot.json(), list)

    # Single points of failure
    res_spof = client.get("/propagation/single-points-of-failure")
    assert res_spof.status_code == 200
    assert isinstance(res_spof.json(), list)

    # Resilience summary
    res_resilience = client.get("/propagation/resilience")
    assert res_resilience.status_code == 200
    assert "mean_resilience_score" in res_resilience.json()


def test_propagation_cli_parser_and_execution():
    """Verify propagation CLI parser building and dispatcher (Spec 79)."""
    parser = build_parser()
    assert parser.prog == "kairo propagation"

    # Test analyze CLI execution
    ret_analyze = main(["analyze", "payment_gw", "--trigger", "Network timeout"])
    assert ret_analyze == 0

    # Test cascades CLI execution
    ret_casc = main(["cascades"])
    assert ret_casc == 0
