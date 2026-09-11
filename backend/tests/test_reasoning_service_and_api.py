"""Integration tests for ReasoningEngineService and REST API (Task 71)."""

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.reasoning.schemas import (
    AssumptionStatus,
    ReasoningConfidence,
    ReasoningDepth,
    ReasoningEvidence,
    ReasoningRequest,
    ReasoningState,
)
from app.reasoning.service import ReasoningEngineService


@pytest.fixture(autouse=True)
def reset_service():
    """Reset service singleton before each test."""
    ReasoningEngineService.reset_instance()
    yield
    ReasoningEngineService.reset_instance()


def test_service_start_session_end_to_end():
    """Verify autonomous execution of deliberation from initiation through completion."""
    service = ReasoningEngineService.get_instance()

    req = ReasoningRequest(
        question="Why did the user authentication service fail during peak traffic?",
        depth=ReasoningDepth.STANDARD,
        risk_level="MEDIUM",
    )

    session = service.start_session(req)

    assert session.reasoning_id
    assert session.current_state == ReasoningState.COMPLETED
    assert len(session.subproblems) > 0
    assert len(session.hypotheses) > 0
    assert len(session.assumptions) > 0
    assert len(session.conclusions) > 0
    assert session.explanation is not None
    assert len(session.trace_events) > 4
    assert session.graph is not None
    assert len(session.graph.nodes) > 0


def test_service_add_evidence_and_falsification_trigger():
    """Verify that adding new evidence tests against falsifiers and triggers re-synthesis."""
    service = ReasoningEngineService.get_instance()

    session = service.start_session(
        ReasoningRequest(
            question="Why did deployment v2.1 cause API errors?",
            depth=ReasoningDepth.QUICK,
        )
    )

    # Add evidence refuting that deployment was the cause
    new_ev = ReasoningEvidence(
        source_type="log",
        source_id="monitor_sys",
        content_summary="Anomaly and latency spike started prior to the deployment timestamp by 45 minutes.",
        trust_level="VERIFIED",
    )

    updated_session = service.add_evidence(session.reasoning_id, new_ev)

    assert len(updated_session.evidence) >= 1
    # Check that trace records refutation cascade
    assert any("EVIDENCE_FALSIFICATION_CASCADE" in e.action for e in updated_session.trace_events)


def test_service_assumption_invalidation_cascade():
    """Verify that invalidating an assumption cascades to conclusions and updates uncertainty."""
    service = ReasoningEngineService.get_instance()

    session = service.start_session(
        ReasoningRequest(
            question="Why did cluster node A become unresponsive?",
            depth=ReasoningDepth.QUICK,
        )
    )

    assert len(session.assumptions) > 0
    asm = session.assumptions[0]

    updated_session, affected = service.invalidate_assumption(
        reasoning_id=session.reasoning_id,
        assumption_id=asm.assumption_id,
        reason="Underlying platform metrics were corrupted during kernel panic.",
    )

    assert len(affected) > 0
    assert asm.assumption_id in [a.assumption_id for a in updated_session.assumptions]
    assert any(a.status == AssumptionStatus.INVALIDATED for a in updated_session.assumptions)
    assert updated_session.confidence == ReasoningConfidence.LOW


def test_service_replay():
    """Verify auditable replay separating trace events and historical evidence."""
    service = ReasoningEngineService.get_instance()

    session = service.start_session(
        ReasoningRequest(
            question="Analyze database replica lag",
            depth=ReasoningDepth.QUICK,
        )
    )

    replay_data = service.replay_session(session.reasoning_id)

    assert replay_data["reasoning_id"] == session.reasoning_id
    assert replay_data["total_trace_events"] > 0
    assert "hypotheses" in replay_data
    assert "conclusion" in replay_data


def test_service_health_metrics():
    """Verify operational health metrics collection."""
    service = ReasoningEngineService.get_instance()
    service.start_session(ReasoningRequest(question="Test Q1", depth=ReasoningDepth.QUICK))
    service.start_session(ReasoningRequest(question="Test Q2", depth=ReasoningDepth.QUICK))

    metrics = service.get_health_metrics()
    assert metrics.completed_count == 2
    assert metrics.total_hypotheses_generated > 0


def test_reasoning_rest_api_endpoints():
    """Verify FastAPI router endpoints for /api/v1/reasoning."""
    app = create_app()
    client = TestClient(app)

    # 1. Health endpoint
    res_health = client.get("/api/v1/reasoning/health")
    assert res_health.status_code == 200
    assert "completed_count" in res_health.json()

    # 2. Start reasoning session
    payload = {
        "question": "Why is caching layer invalidation failing for multi-tenant accounts?",
        "depth": "STANDARD",
        "risk_level": "HIGH",
    }
    res_start = client.post("/api/v1/reasoning/start", json=payload)
    assert res_start.status_code == 201
    data = res_start.json()
    reasoning_id = data["reasoning_id"]
    assert reasoning_id
    assert data["current_state"] == "COMPLETED"

    # 3. Get session
    res_get = client.get(f"/api/v1/reasoning/{reasoning_id}")
    assert res_get.status_code == 200
    assert res_get.json()["reasoning_id"] == reasoning_id

    # 4. Get hypotheses
    res_hyps = client.get(f"/api/v1/reasoning/{reasoning_id}/hypotheses")
    assert res_hyps.status_code == 200
    assert isinstance(res_hyps.json(), list)

    # 5. Get evidence
    res_evd = client.get(f"/api/v1/reasoning/{reasoning_id}/evidence")
    assert res_evd.status_code == 200

    # 6. Add evidence
    res_add_evd = client.post(
        f"/api/v1/reasoning/{reasoning_id}/evidence",
        json={
            "content_summary": "Redis cluster node was restarted 2 minutes ago",
            "trust_level": "VERIFIED",
            "reliability": 0.95,
        },
    )
    assert res_add_evd.status_code == 200

    # 7. Get assumptions
    res_asm = client.get(f"/api/v1/reasoning/{reasoning_id}/assumptions")
    assert res_asm.status_code == 200
    asms = res_asm.json()
    assert len(asms) > 0

    # 8. Invalidate assumption
    asm_id = asms[0]["assumption_id"]
    res_inv = client.post(
        f"/api/v1/reasoning/{reasoning_id}/assumptions/{asm_id}/invalidate",
        json={"reason": "Config key changed in tenant namespace"},
    )
    assert res_inv.status_code == 200
    assert res_inv.json()["assumption_id"] == asm_id

    # 9. Get conclusion & explanation
    res_concl = client.get(f"/api/v1/reasoning/{reasoning_id}/conclusion")
    assert res_concl.status_code == 200
    assert "summary" in res_concl.json()

    res_expl = client.get(f"/api/v1/reasoning/{reasoning_id}/explanation")
    assert res_expl.status_code == 200
    assert "conclusion_summary" in res_expl.json()

    # 10. Get trace & graph & quality
    res_trace = client.get(f"/api/v1/reasoning/{reasoning_id}/trace")
    assert res_trace.status_code == 200

    res_graph = client.get(f"/api/v1/reasoning/{reasoning_id}/graph")
    assert res_graph.status_code == 200
    assert "nodes" in res_graph.json()

    res_qual = client.get(f"/api/v1/reasoning/{reasoning_id}/quality")
    assert res_qual.status_code == 200
    assert "reasoning_quality_score" in res_qual.json()

    # 11. Replay
    res_replay = client.get(f"/api/v1/reasoning/{reasoning_id}/replay")
    assert res_replay.status_code == 200
    assert res_replay.json()["reasoning_id"] == reasoning_id

    # 12. List sessions
    res_list = client.get("/api/v1/reasoning/sessions")
    assert res_list.status_code == 200
    assert len(res_list.json()) >= 1
