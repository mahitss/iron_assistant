"""Tests for Situational Awareness Synthesis, Relevance Engine, Perception Service Pipeline, and REST API (Task 46)."""

from datetime import datetime, timezone
import pytest
from starlette.testclient import TestClient

from app.main import create_app
from app.perception.context import PerceptionContext, RelevanceEngine
from app.perception.events import EventType, PerceptionEvent
from app.perception.observations import Observation
from app.perception.service import PerceptionService
from app.perception.situation import SituationalAwarenessManager
from app.perception.sources import PerceptionSource, SourceStatus, SourceType


def utc_now():
    return datetime.now(timezone.utc)


def test_situational_awareness_distinguishes_fact_and_inference():
    """Enforce Spec 101-106: Clearly distinguish observed facts vs inferences; missing sources remain unknown."""
    mgr = SituationalAwarenessManager()
    source = PerceptionSource("src_1", SourceType.SERVICE, "Auth Svc")

    obs = Observation.from_event(
        PerceptionEvent("e1", EventType.UPDATED, "src_1", "service:auth", payload={"status": "HEALTHY"}),
        source,
    )

    sit = mgr.synthesize_situation(
        scope={"environment": "PRODUCTION"},
        observations=[obs],
        changes=[],
        anomalies=[],
        active_tasks=["deploy_v2"],
        unknown_sources=["billing_engine"],
    )

    assert sit.version == 1
    assert "PRODUCTION" in sit.scope.get("environment", "")
    assert len(sit.observed_facts) == 1
    assert "service:auth" in sit.observed_facts[0]
    # Missing source recorded as uncertainty (Spec 103)
    assert any("billing_engine" in u for u in sit.uncertainties)


def test_relevance_engine_ranking():
    """Enforce Spec 107-110: Rank observations based on current task, risk, recency, and scope."""
    ctx = PerceptionContext(
        task_id="task_build_image",
        project_id="kairo_core",
        environment="DEVELOPMENT",
    )

    source = PerceptionSource("src_1", SourceType.TASK_ENGINE, "Task Engine")

    # Observation matching task
    obs_task = Observation.from_event(
        PerceptionEvent("e_t", EventType.UPDATED, "src_1", "task:task_build_image", payload={"status": "BUILDING"}, scope={"project_id": "kairo_core"}),
        source,
    )
    # Observation in same project but unrelated to task
    obs_general = Observation.from_event(
        PerceptionEvent("e_g", EventType.UPDATED, "src_1", "service:weather", payload={"temp": 20}, scope={"project_id": "kairo_core"}),
        source,
    )
    # Observation in different project (should be excluded by project boundary)
    obs_other_proj = Observation.from_event(
        PerceptionEvent("e_o", EventType.UPDATED, "src_1", "service:secret", payload={"val": 1}, scope={"project_id": "other_proj"}),
        source,
    )

    ranked = RelevanceEngine.rank_observations([obs_general, obs_other_proj, obs_task], context=ctx, max_items=5)
    assert len(ranked) == 2
    # obs_task should be ranked first due to task matching
    assert ranked[0].observation_id == obs_task.observation_id
    assert ranked[1].observation_id == obs_general.observation_id


def test_perception_service_end_to_end_pipeline():
    """Test canonical ingestion pipeline:
    INGEST -> AUTH -> REDACT -> NORMALIZE -> DEDUP -> ORDER -> FRESHNESS -> OBSERVE -> PROVENANCE -> CORRELATE -> RECONCILE -> CHANGE -> ANOMALY -> SITUATION.
    """
    service = PerceptionService()
    source = service.sources.register_source(
        source_type=SourceType.SERVICE,
        name="Order Processing Service",
        reliability=0.95,
    )

    raw_event = {
        "action": "STATUS_CHANGED",
        "service_name": "order_svc",
        "status": "HEALTHY",
        "latency_ms": 22.5,
        "api_key": "sk-secret12345678901234567890",  # should be redacted
    }

    res = service.ingest_event(
        raw_event=raw_event,
        source_id=source.source_id,
        user_id="default_user",
        project_id="default_project",
        environment="DEVELOPMENT",
    )

    assert res is not None
    obs, chg, anom = res

    # Observation created
    assert obs.subject == "service:order_svc"
    assert obs.confidence == 0.95
    # Redaction verified
    prov = service.provenance_tracker.get_provenance(obs.observation_id)
    assert prov is not None
    assert prov.redaction_applied is True

    # Change detected
    assert chg is not None
    assert chg.subject == "service:order_svc"

    # Liveness heartbeat recorded
    src = service.sources.get_source(source.source_id)
    assert src.status == SourceStatus.HEALTHY


def test_perception_rest_api_endpoints():
    app = create_app()
    client = TestClient(app)

    # 1. Register Source
    reg_resp = client.post("/api/v1/perception/sources", json={
        "type": "SERVICE",
        "name": "User Auth API",
        "capabilities": ["health", "metrics"],
        "reliability": 0.98,
        "privacy_level": "INTERNAL",
    })
    assert reg_resp.status_code == 201
    source_id = reg_resp.json()["source_id"]

    # 2. List Sources
    list_resp = client.get("/api/v1/perception/sources")
    assert list_resp.status_code == 200
    assert any(s["source_id"] == source_id for s in list_resp.json())

    # 3. Ingest Event
    evt_resp = client.post(f"/api/v1/perception/sources/{source_id}/events", json={
        "event_type": "HEALTH_CHANGED",
        "subject": "service:auth_api",
        "payload": {"status": "HEALTHY", "latency": 10},
    })
    assert evt_resp.status_code == 200
    assert evt_resp.json()["status"] == "PROCESSED"
    assert evt_resp.json()["subject"] == "service:auth_api"

    # 4. Get Recent Observations
    obs_resp = client.get("/api/v1/perception/observations")
    assert obs_resp.status_code == 200
    assert len(obs_resp.json()) >= 1

    # 5. Get Recent Changes
    chg_resp = client.get("/api/v1/perception/changes")
    assert chg_resp.status_code == 200

    # 6. Capture Snapshot
    snap_resp = client.post("/api/v1/perception/snapshots", json={
        "environment": "DEVELOPMENT",
        "is_atomic": True,
    })
    assert snap_resp.status_code == 201
    assert snap_resp.json()["environment"] == "DEVELOPMENT"

    # 7. Get Live Situation
    sit_resp = client.get("/api/v1/perception/situation")
    assert sit_resp.status_code == 200
    assert "summary" in sit_resp.json()

    # 8. Get Perception Health
    hlth_resp = client.get("/api/v1/perception/health")
    assert hlth_resp.status_code == 200
    assert hlth_resp.json()["events_processed"] >= 1

    # 9. Disable Source
    dis_resp = client.post(f"/api/v1/perception/sources/{source_id}/disable")
    assert dis_resp.status_code == 200
    assert dis_resp.json()["status"] == "DISABLED"
