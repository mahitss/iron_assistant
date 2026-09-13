"""Unit and integration tests for Governance REST API endpoints and CLI commands (Task 78)."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.policy.cli import build_parser, handle_command
from app.policy.governance_coordinator import default_governance_coordinator
from app.policy.governance_router import router as governance_router
from app.policy.governance_schemas import AuthorityLevel, GovernanceReviewRequest


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()
    app.include_router(governance_router, prefix="/api/v1")
    return TestClient(app)


# ==============================================================================
# REST API Endpoint Tests
# ==============================================================================

def test_api_dashboard_summary(client: TestClient) -> None:
    """GET /api/v1/governance/dashboard returns valid metrics."""
    res = client.get("/api/v1/governance/dashboard")
    assert res.status_code == 200
    data = res.json()
    assert "active_policies_by_tier" in data
    assert "constitutional_compliance_index" in data
    assert data["constitutional_compliance_index"] >= 0.0


def test_api_constitution_endpoints(client: TestClient) -> None:
    """GET constitution and PUT principle update (with admin header)."""
    # 1. GET constitution
    res = client.get("/api/v1/governance/constitution")
    assert res.status_code == 200
    c_data = res.json()
    assert len(c_data["principles"]) == 11

    # 2. PUT principle update without admin header -> 403
    res_no_admin = client.put(
        "/api/v1/governance/constitution/principles/safety",
        json={"weight": 0.99},
    )
    assert res_no_admin.status_code == 403

    # 3. PUT principle update with admin header -> 200
    res_admin = client.put(
        "/api/v1/governance/constitution/principles/safety",
        json={"weight": 0.99},
        headers={"x-user-role": "admin", "x-user-id": "admin_1"},
    )
    assert res_admin.status_code == 200
    assert res_admin.json()["status"] == "success"


def test_api_authority_grant_lifecycle(client: TestClient) -> None:
    """POST /authority/grant, GET /authority/{subject}, and DELETE /authority/{subject}."""
    # 1. Issue grant
    res_grant = client.post(
        "/api/v1/governance/authority/grant",
        json={
            "subject_id": "test_agent_api",
            "authority_level": "PROJECT",
            "allowed_scopes": ["scope_a"],
            "allowed_actions": ["action_a"],
        },
    )
    assert res_grant.status_code == 201
    g_data = res_grant.json()
    assert g_data["subject_id"] == "test_agent_api"
    assert g_data["authority_level"] == "PROJECT"

    # 2. Get authority
    res_get = client.get("/api/v1/governance/authority/test_agent_api")
    assert res_get.status_code == 200
    auth_data = res_get.json()
    assert auth_data["highest_authority_level"] == "PROJECT"
    assert auth_data["active_grants_count"] >= 1

    # 3. Revoke authority
    res_del = client.delete("/api/v1/governance/authority/test_agent_api")
    assert res_del.status_code == 200
    assert res_del.json()["revoked_grants_count"] >= 1


def test_api_review_and_human_resolution_lifecycle(client: TestClient) -> None:
    """POST /review -> REQUIRES_HUMAN -> POST /reviews/{id}/resolve."""
    # 0. Issue authority grant for storage_agent
    default_governance_coordinator.authority_manager.issue_grant(
        subject_id="storage_agent",
        authority_level=AuthorityLevel.PROJECT,
        allowed_actions=["repartition_*", "format_*"],
    )

    # 1. Submit review requiring human judgment (irreversible high-uncertainty operation)
    req_body = {
        "goal": "Rebalance cluster partitions",
        "action": "repartition_cluster_nodes",
        "resource": "cluster_nodes",
        "caller_id": "storage_agent",
        "caller_authority": "PROJECT",
        "risk_level": "R3_HIGH",
        "is_destructive": False,
        "is_irreversible": True,
        "uncertainty_score": 0.85,
    }
    res_rev = client.post("/api/v1/governance/review", json=req_body)
    assert res_rev.status_code == 200
    rev_data = res_rev.json()
    review_id = rev_data["review_id"]
    assert rev_data["decision"] == "REQUIRES_HUMAN"
    assert rev_data["requires_human"] is True

    # 2. Verify it shows in pending-human list
    res_pending = client.get("/api/v1/governance/reviews/pending-human")
    assert res_pending.status_code == 200
    pending_ids = [r["review_id"] for r in res_pending.json()]
    assert review_id in pending_ids

    # 3. Self-approval by AI agent rejected -> 403 or 400
    res_self = client.post(
        f"/api/v1/governance/reviews/{review_id}/resolve",
        json={"reviewer_id": "kairo", "approved": True, "rationale": "I self-approve."},
        headers={"x-caller-type": "agent"},
    )
    assert res_self.status_code in (400, 403)

    # 4. Human operator approval -> 200
    res_human = client.post(
        f"/api/v1/governance/reviews/{review_id}/resolve",
        json={"reviewer_id": "human_admin_jane", "approved": True, "rationale": "Verified safe."},
    )
    assert res_human.status_code == 200
    resolved_data = res_human.json()
    assert resolved_data["state"] == "EXECUTABLE"
    assert resolved_data["decision"] == "ALLOWED"


# ==============================================================================
# CLI Command Tests
# ==============================================================================

def test_cli_parser_build() -> None:
    """Verify CLI parser builds with all subcommands."""
    parser = build_parser()
    assert parser is not None


def test_cli_review_and_dashboard_execution(capsys: pytest.CaptureFixture[str]) -> None:
    """Execute CLI commands and verify clean exit code 0."""
    parser = build_parser()

    # 1. Dashboard command
    args_dash = parser.parse_args(["dashboard"])
    code_dash = handle_command(args_dash)
    assert code_dash == 0

    # 2. Review command
    args_rev = parser.parse_args([
        "review",
        "--goal", "List cluster status",
        "--action", "read_cluster_status",
        "--authority", "LIMITED",
    ])
    code_rev = handle_command(args_rev)
    assert code_rev == 0

    # 3. Constitution show command
    args_const = parser.parse_args(["constitution", "show"])
    code_const = handle_command(args_const)
    assert code_const == 0

    # 4. Authority grant and check
    args_grant = parser.parse_args([
        "authority", "grant",
        "--subject", "cli_test_agent",
        "--level", "LIMITED",
        "--actions", "cli_action_*",
    ])
    assert handle_command(args_grant) == 0

    args_check = parser.parse_args([
        "authority", "check",
        "--subject", "cli_test_agent",
        "--action", "cli_action_test",
    ])
    assert handle_command(args_check) == 0
