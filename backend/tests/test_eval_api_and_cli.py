"""
Unit tests for Kairo evaluation REST API endpoints and CLI commands.
Verifies HTTP endpoints, baseline comparisons, security dashboard, and CLI parsers.
"""

import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from app.main import create_app
from app.evaluation.cli import build_parser, handle_list
from app.evaluation.registry import ScenarioRegistry


@pytest.fixture(scope="module")
def client():
    """FastAPI test client instance."""
    app = create_app()
    with TestClient(app) as tc:
        yield tc


def test_api_list_scenarios_and_suites(client: TestClient):
    """Verify /api/v1/evaluation/scenarios and /suites endpoints."""
    # List all scenarios
    res_scenarios = client.get("/api/v1/evaluation/scenarios")
    assert res_scenarios.status_code == 200
    scenarios = res_scenarios.json()
    assert isinstance(scenarios, list)
    assert len(scenarios) >= 5

    # Filter by category
    res_sec = client.get("/api/v1/evaluation/scenarios?category=security")
    assert res_sec.status_code == 200
    sec_scenarios = res_sec.json()
    assert all(s["category"] == "security" for s in sec_scenarios)

    # List suites
    res_suites = client.get("/api/v1/evaluation/suites")
    assert res_suites.status_code == 200
    suites = res_suites.json()
    assert "security" in suites
    assert "full" in suites


def test_api_trigger_evaluation_run(client: TestClient):
    """Verify POST /api/v1/evaluation/run executes mock evaluation suite."""
    payload = {
        "suite": "routing",
        "multi_run_count": 1,
        "mode": "LOCAL",
    }
    response = client.post("/api/v1/evaluation/run", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert "run_id" in data
    assert data["suite_name"] == "routing"
    assert "metrics" in data
    assert data["metrics"]["total_scenarios"] >= 1
    assert data["release_blocked"] is False

    run_id = data["run_id"]

    # Verify run detail can be retrieved
    res_detail = client.get(f"/api/v1/evaluation/runs/{run_id}")
    assert res_detail.status_code == 200
    detail_data = res_detail.json()
    assert detail_data["run_id"] == run_id


def test_api_baselines_and_comparison(client: TestClient):
    """Verify /api/v1/evaluation/baselines and /compare endpoints."""
    res_baselines = client.get("/api/v1/evaluation/baselines")
    assert res_baselines.status_code == 200
    baselines = res_baselines.json()
    assert "v1.0.0" in baselines

    # Compare without prior run (or with current state)
    res_compare = client.get("/api/v1/evaluation/compare?baseline_version=v1.0.0")
    assert res_compare.status_code == 200
    comp_data = res_compare.json()
    assert "baseline_version" in comp_data
    assert comp_data["baseline_version"] == "v1.0.0"
    assert "release_blocked" in comp_data


def test_api_security_dashboard(client: TestClient):
    """Verify /api/v1/evaluation/security returns distinct security control statuses."""
    res = client.get("/api/v1/evaluation/security")
    assert res.status_code == 200
    sec_data = res.json()
    assert "security_pass_rate" in sec_data
    assert "controls" in sec_data
    assert sec_data["security_pass_rate"] == 1.0


def test_cli_parser_and_list_command():
    """Verify CLI parser options and handle_list output."""
    parser = build_parser()

    # Test list args
    args_list = parser.parse_args(["list", "--category", "security"])
    assert args_list.command == "list"
    assert args_list.category == "security"

    # Test run args
    args_run = parser.parse_args(["run", "--suite", "security", "--mode", "CI", "--multi-run", "3"])
    assert args_run.command == "run"
    assert args_run.suite == "security"
    assert args_run.mode == "CI"
    assert args_run.multi_run == 3

    # Test compare args
    args_comp = parser.parse_args(["compare", "--baseline", "v1.0.0"])
    assert args_comp.command == "compare"
    assert args_comp.baseline == "v1.0.0"

    # Test handle_list execution
    evals_dir = Path(__file__).resolve().parent.parent.parent / "evals"
    registry = ScenarioRegistry(evals_dir=evals_dir)
    registry.load_all()

    import asyncio
    exit_code = asyncio.run(handle_list(args_list, registry))
    assert exit_code == 0
