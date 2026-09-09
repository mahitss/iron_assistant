"""Integration tests for Multi-Agent Collaboration REST API endpoints (Task 44)."""

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_collaboration_session_lifecycle(client: TestClient):
    # 1. Create session
    resp = client.post(
        "/api/v1/collaboration/sessions",
        json={
            "goal": "Refactor authentication subsystem to support WebAuthn",
            "project_id": "proj_kairo",
            "risk_level": "high",
        },
        headers={"x-user-id": "test_lead"},
    )
    assert resp.status_code == status.HTTP_201_CREATED
    data = resp.json()
    assert "session_id" in data
    session_id = data["session_id"]
    assert data["goal"] == "Refactor authentication subsystem to support WebAuthn"
    assert data["user_id"] == "test_lead"

    # 2. Get session details
    get_resp = client.get(f"/api/v1/collaboration/sessions/{session_id}")
    assert get_resp.status_code == status.HTTP_200_OK
    assert get_resp.json()["session_id"] == session_id


def test_agent_registration_and_discovery(client: TestClient):
    # Register specialist agent
    resp = client.post(
        "/api/v1/collaboration/agents",
        json={
            "name": "WebAuthn Specialist",
            "role": "SECURITY_ANALYST",
            "capabilities": ["webauthn", "fido2", "crypto_audit"],
            "model_profile": "claude-3-5-sonnet",
            "max_tokens": 40000,
            "max_cost": 0.8,
        },
    )
    assert resp.status_code == status.HTTP_201_CREATED
    data = resp.json()
    assert "agent_id" in data
    assert data["role"] == "SECURITY_ANALYST"
    agent_id = data["agent_id"]

    # List agents
    list_resp = client.get("/api/v1/collaboration/agents?role=SECURITY_ANALYST")
    assert list_resp.status_code == status.HTTP_200_OK
    agents = list_resp.json()
    assert any(a["agent_id"] == agent_id for a in agents)


def test_contracts_and_expansion(client: TestClient):
    # 1. Create agent
    ag_resp = client.post(
        "/api/v1/collaboration/agents",
        json={
            "name": "Backend Coder",
            "role": "CODER",
            "capabilities": ["python", "fastapi"],
        },
    )
    agent_id = ag_resp.json()["agent_id"]

    # 2. Create contract
    ct_resp = client.post(
        "/api/v1/collaboration/contracts",
        json={
            "agent_id": agent_id,
            "parent_goal": "Implement WebAuthn Endpoints",
            "assigned_objective": "Write WebAuthn challenge generation route",
            "scope_resources": ["backend/app/auth/webauthn.py"],
            "scope_tools": ["code_read_file"],
            "token_budget": 5000,
        },
    )
    assert ct_resp.status_code == status.HTTP_201_CREATED
    ct_data = ct_resp.json()
    contract_id = ct_data["contract_id"]
    assert ct_data["status"] == "ACTIVE"

    # 3. Request contract expansion
    exp_resp = client.post(
        "/api/v1/collaboration/contracts/expand",
        json={
            "contract_id": contract_id,
            "reason": "Need code edit tool and access to models directory",
            "requested_resources": ["backend/app/auth/models.py"],
            "requested_tools": ["code_search"],
            "requested_token_budget": 10000,
        },
    )
    assert exp_resp.status_code == status.HTTP_200_OK
    assert "code_search" in exp_resp.json()["scope"]["tools"]


def test_evidence_and_consensus_api(client: TestClient):
    # Create evidence 1 (verified)
    ev_resp1 = client.post(
        "/api/v1/collaboration/evidence",
        json={
            "session_id": "test_sess_1",
            "producer_agent_id": "agent_1",
            "contract_id": "ct_1",
            "fact_type": "FACT",
            "claim": "FIDO2 library requires PyCryptodome >= 3.19",
            "sources": ["requirements.txt"],
            "is_verified": True,
        },
    )
    assert ev_resp1.status_code == status.HTTP_201_CREATED
    ev1_id = ev_resp1.json()["evidence_id"]

    # Create evidence 2 (unverified hypothesis)
    ev_resp2 = client.post(
        "/api/v1/collaboration/evidence",
        json={
            "session_id": "test_sess_1",
            "producer_agent_id": "agent_2",
            "contract_id": "ct_2",
            "fact_type": "HYPOTHESIS",
            "claim": "FIDO2 might work on older PyCryptodome",
            "is_verified": False,
        },
    )
    assert ev_resp2.status_code == status.HTTP_201_CREATED
    ev2_id = ev_resp2.json()["evidence_id"]

    # Check consensus - verified evidence wins
    con_resp = client.post(
        "/api/v1/collaboration/consensus",
        json={
            "topic": "PyCryptodome version requirement",
            "evidence_ids": [ev1_id, ev2_id],
        },
    )
    assert con_resp.status_code == status.HTTP_200_OK
    con_data = con_resp.json()
    assert con_data["status"] == "EVIDENCE_SUPPORTED"
    assert "PyCryptodome >= 3.19" in con_data["verified_claim"]


def test_emergency_stop_api(client: TestClient):
    # Create session
    sess_resp = client.post(
        "/api/v1/collaboration/sessions",
        json={"goal": "High risk task"},
    )
    session_id = sess_resp.json()["session_id"]

    # Trigger emergency stop
    stop_resp = client.post(
        "/api/v1/collaboration/emergency-stop",
        json={
            "session_id": session_id,
            "reason": "Security invariant violation detected",
            "triggered_by": "SUPERVISOR",
        },
    )
    assert stop_resp.status_code == status.HTTP_200_OK
    assert stop_resp.json()["stopped"] is True

    # Verify session is stopped
    check_resp = client.get(f"/api/v1/collaboration/sessions/{session_id}")
    assert check_resp.json()["status"] == "EMERGENCY_STOPPED"


def test_provenance_api(client: TestClient):
    sess_resp = client.post(
        "/api/v1/collaboration/sessions",
        json={"goal": "Traceable goal"},
    )
    session_id = sess_resp.json()["session_id"]

    prov_resp = client.get(f"/api/v1/collaboration/provenance/{session_id}")
    assert prov_resp.status_code == status.HTTP_200_OK
    prov_data = prov_resp.json()
    assert prov_data["session_id"] == session_id
    assert prov_data["node_count"] >= 1
