"""Tests for Normalized Perception Events, 27 Event Types, Adapters, Deduplication, and Ordering (Task 46)."""

from datetime import datetime, timezone
import pytest

from app.perception.adapters import (
    AgentAdapter,
    AutomationAdapter,
    BrowserAdapter,
    CalendarAdapter,
    DeploymentAdapter,
    DeviceAdapter,
    FileSystemAdapter,
    GitAdapter,
    GitHubAdapter,
    NotificationAdapter,
    ServiceHealthAdapter,
    TaskEngineAdapter,
    VisionAdapter,
    VoiceAdapter,
)
from app.perception.deduplication import EventDeduplicator
from app.perception.events import (
    EventAuthenticityError,
    EventType,
    InvalidEventError,
    PayloadSizeExceededError,
    PerceptionEvent,
)
from app.perception.normalizer import EventNormalizer
from app.perception.ordering import EventOrderManager
from app.perception.sources import PerceptionSource, SourceType


def utc_now():
    return datetime.now(timezone.utc)


def test_27_environmental_event_types():
    types = [
        "CREATED", "UPDATED", "DELETED", "STARTED", "STOPPED", "CONNECTED",
        "DISCONNECTED", "FAILED", "RECOVERED", "HEALTH_CHANGED", "STATUS_CHANGED",
        "DEPLOYED", "COMMITTED", "PUSHED", "MERGED", "OPENED", "CLOSED",
        "FOCUSED", "NAVIGATED", "RECEIVED", "SENT", "SCHEDULED", "CANCELLED",
        "COMPLETED", "BLOCKED", "EXPIRED", "ALERTED",
    ]
    for t in types:
        assert EventType(t) is not None


def test_event_validation_and_rejection():
    # Valid event
    evt = PerceptionEvent(
        event_id="evt_valid",
        event_type=EventType.UPDATED,
        source_id="src_1",
        subject="device:laptop",
        payload={"status": "online"},
    )
    evt.validate()

    # Missing mandatory field: subject
    invalid_evt = PerceptionEvent(
        event_id="evt_invalid",
        event_type=EventType.UPDATED,
        source_id="src_1",
        subject="",
    )
    with pytest.raises(InvalidEventError):
        invalid_evt.validate()

    # Payload size limit bound (Spec 150)
    huge_payload = {"key": "x" * (600 * 1024)}  # 600 KB > 512 KB
    oversized_evt = PerceptionEvent(
        event_id="evt_huge",
        event_type=EventType.UPDATED,
        source_id="src_1",
        subject="file:blob",
        payload=huge_payload,
    )
    with pytest.raises(PayloadSizeExceededError):
        oversized_evt.validate()

    # Authenticity verification (Spec 14, 15)
    unauth_evt = PerceptionEvent(
        event_id="evt_unauth",
        event_type=EventType.CREATED,
        source_id="src_rogue",
        subject="system:root",
        is_authenticated=False,
    )
    with pytest.raises(EventAuthenticityError):
        unauth_evt.validate()


def test_event_deduplication_and_idempotency():
    dedup = EventDeduplicator()
    t = utc_now()
    evt1 = PerceptionEvent(
        event_id="evt_101",
        event_type=EventType.COMMITTED,
        source_id="src_git",
        subject="git:repo",
        timestamp=t,
        payload={"hash": "abc123"},
    )
    evt2 = PerceptionEvent(
        event_id="evt_102",  # different event id but identical semantic event
        event_type=EventType.COMMITTED,
        source_id="src_git",
        subject="git:repo",
        timestamp=t,
        payload={"hash": "abc123"},
    )

    # First ingestion is new
    assert dedup.is_duplicate(evt1) is False

    # Second identical ingestion is flagged duplicate (Spec 16, 17)
    assert dedup.is_duplicate(evt2) is True


def test_event_ordering_and_out_of_order_tracking():
    order_mgr = EventOrderManager()

    e1 = PerceptionEvent("e1", EventType.UPDATED, "src_dev", "device:laptop", sequence=1)
    e2 = PerceptionEvent("e2", EventType.UPDATED, "src_dev", "device:laptop", sequence=2)
    e_late = PerceptionEvent("e_late", EventType.UPDATED, "src_dev", "device:laptop", sequence=1)

    ok, status = order_mgr.check_sequence(e1)
    assert ok is True
    assert status == "IN_ORDER"

    ok, status = order_mgr.check_sequence(e2)
    assert ok is True
    assert status == "IN_ORDER"

    # Out-of-order sequence <= last known sequence
    ok, status = order_mgr.check_sequence(e_late)
    assert ok is False
    assert status == "OUT_OF_ORDER"


def test_adapters_device_and_browser():
    source_dev = PerceptionSource("src_dev", SourceType.DEVICE, "Local Laptop")
    dev_adapt = DeviceAdapter()
    dev_evt = dev_adapt.adapt({
        "action": "STATUS_CHANGED",
        "device_id": "laptop_123",
        "battery_level": 92,
        "is_charging": False,
        "network_ssid": "HomeNet",
    }, source_dev)
    assert dev_evt.subject == "device:laptop_123"
    assert dev_evt.payload["battery_level"] == 92
    assert dev_evt.payload["is_charging"] is False

    source_brw = PerceptionSource("src_brw", SourceType.BROWSER, "Chrome Extension")
    brw_adapt = BrowserAdapter()
    brw_evt = brw_adapt.adapt({
        "action": "NAVIGATED",
        "url": "https://github.com/mahitss/iron_assistant",
        "title": "GitHub Repo",
        "tab_id": 42,
    }, source_brw)
    assert brw_evt.event_type == EventType.NAVIGATED
    assert brw_evt.subject == "browser:tab_42"
    assert brw_evt.payload["url"] == "https://github.com/mahitss/iron_assistant"


def test_adapters_git_github_deployment_and_service():
    source_git = PerceptionSource("src_git", SourceType.GIT, "Git VCS")
    git_adapt = GitAdapter()
    git_evt = git_adapt.adapt({
        "repository": "kairo_core",
        "commit_hash": "a1b2c3d",
        "branch": "feat/perception",
    }, source_git)
    assert git_evt.event_type == EventType.COMMITTED
    assert git_evt.correlation_id == "a1b2c3d"

    source_gh = PerceptionSource("src_gh", SourceType.GITHUB, "GitHub Webhook")
    gh_adapt = GitHubAdapter()
    gh_evt = gh_adapt.adapt({
        "repository": "kairo_core",
        "github_type": "pull_request",
        "number": 88,
        "title": "Add perception engine",
    }, source_gh)
    assert gh_evt.subject == "github:kairo_core:pull_request_88"

    source_dep = PerceptionSource("src_dep", SourceType.DEPLOYMENT, "ArgoCD")
    dep_adapt = DeploymentAdapter()
    dep_evt = dep_adapt.adapt({
        "service": "kairo-api",
        "environment": "PRODUCTION",
        "version": "v1.4.0",
        "commit_hash": "a1b2c3d",
    }, source_dep)
    assert dep_evt.event_type == EventType.DEPLOYED
    assert dep_evt.causation_id == "a1b2c3d"

    source_svc = PerceptionSource("src_svc", SourceType.SERVICE, "Health Prober")
    svc_adapt = ServiceHealthAdapter()
    svc_evt = svc_adapt.adapt({
        "service_name": "auth-service",
        "status": "HEALTHY",
        "latency_ms": 15.2,
    }, source_svc)
    assert svc_evt.subject == "service:auth-service"
    assert svc_evt.payload["status"] == "HEALTHY"


def test_adapters_voice_vision_task_agent_automation_calendar():
    source_voc = PerceptionSource("src_voc", SourceType.VOICE, "Mic Stream")
    voc_adapt = VoiceAdapter()
    voc_evt = voc_adapt.adapt({"transcription": "deploy to staging", "confidence": 0.98}, source_voc)
    assert voc_evt.payload["transcription"] == "deploy to staging"
    # Never persist raw audio
    assert "audio_bytes" not in voc_evt.payload

    source_vis = PerceptionSource("src_vis", SourceType.VISION, "Camera Sensor")
    vis_adapt = VisionAdapter()
    vis_evt = vis_adapt.adapt({
        "detected_object": "laptop_screen",
        "interpreted_meaning": "IDE open",
        "inference": "developer working",
    }, source_vis)
    assert vis_evt.payload["detected_object"] == "laptop_screen"
    assert vis_evt.payload["interpreted_meaning"] == "IDE open"

    source_tsk = PerceptionSource("src_tsk", SourceType.TASK_ENGINE, "Task Engine")
    tsk_adapt = TaskEngineAdapter()
    tsk_evt = tsk_adapt.adapt({"task_id": "tsk_99", "action": "PROGRESS", "progress_pct": 50}, source_tsk)
    assert tsk_evt.subject == "task:tsk_99"

    source_ag = PerceptionSource("src_ag", SourceType.AGENT, "Collaboration Agent")
    ag_adapt = AgentAdapter()
    ag_evt = ag_adapt.adapt({"agent_id": "coder_agent", "action": "WORKING"}, source_ag)
    assert ag_evt.subject == "agent:coder_agent"

    source_aut = PerceptionSource("src_aut", SourceType.AUTOMATION, "Scheduler")
    aut_adapt = AutomationAdapter()
    aut_evt = aut_adapt.adapt({"workflow_id": "nightly_backup"}, source_aut)
    assert aut_evt.subject == "automation:nightly_backup"

    source_cal = PerceptionSource("src_cal", SourceType.CALENDAR, "Google Calendar")
    cal_adapt = CalendarAdapter()
    cal_evt = cal_adapt.adapt({"event_id": "sprint_demo", "action": "UPCOMING"}, source_cal)
    assert cal_evt.subject == "calendar:sprint_demo"
