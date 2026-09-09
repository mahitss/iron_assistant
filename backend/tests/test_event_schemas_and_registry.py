"""Tests for Event schemas, canonical validation, and the Central Event Registry."""

import pytest
from datetime import datetime, timezone

from app.events.schemas import (
    Event,
    EventSource,
    ReplaySafety,
    EventStatus,
    GithubCiFailedPayload,
    ChatMessageCreatedPayload,
    SecurityBlockedPayload,
    ApprovalRequestedPayload,
    EmergencyStopActivatedPayload,
)
from app.events.registry import event_registry, EventRegistry, EventRegistration, EventSecurityClass


def test_canonical_event_creation():
    event = Event(
        event_id="evt_test_123",
        event_type="github.ci.failed",
        event_version="1.0.0",
        timestamp=datetime.now(timezone.utc),
        source=EventSource.GITHUB_WEBHOOK.value,
        user_id="user_1",
        project_id="proj_1",
        correlation_id="corr_1",
        causation_id="caus_1",
        payload={"repo": "kairo/core", "workflow_name": "CI"},
        metadata={"priority": "high"},
    )
    assert event.event_id == "evt_test_123"
    assert event.event_type == "github.ci.failed"
    assert event.source == "github_webhook"
    assert event.payload["repo"] == "kairo/core"


def test_typed_payload_schemas():
    gh_payload = GithubCiFailedPayload(
        repo="kairo/assistant",
        workflow_name="Test Suite",
        run_id="12345",
        failure_summary="AssertionError in line 42",
    )
    assert gh_payload.repo == "kairo/assistant"

    chat_payload = ChatMessageCreatedPayload(
        session_id="sess_abc",
        message="Hello Kairo",
        role="user",
    )
    assert chat_payload.role == "user"

    sec_payload = SecurityBlockedPayload(
        tool_name="bash_execute",
        reason="Command not in allowed list",
        risk_level="HIGH",
    )
    assert sec_payload.risk_level == "HIGH"


def test_event_registry_has_core_namespaces():
    catalog = event_registry.list_all()
    types = [e.event_type for e in catalog]

    # Verify canonical namespaces exist
    expected_namespaces = [
        "chat.message.created",
        "chat.response.completed",
        "github.ci.failed",
        "github.pr.merged",
        "security.blocked",
        "approval.requested",
        "approval.granted",
        "emergency_stop.activated",
        "device.connected",
        "device.revoked",
        "notification.created",
        "evaluation.completed",
    ]
    for ns in expected_namespaces:
        assert ns in types, f"Missing expected namespace in registry: {ns}"


def test_replay_safety_classification():
    # Non-replayable events
    non_replayable = ["github.write", "computer.action.requested", "device.revoked", "emergency_stop.activated"]
    for nr in non_replayable:
        defn = event_registry.get(nr)
        if defn:
            assert defn.replay_safety == ReplaySafety.NON_REPLAYABLE, f"{nr} must be NON_REPLAYABLE"

    # Replay-safe events
    replay_safe = ["knowledge.index.requested", "notification.read", "vision.requested"]
    for rs in replay_safe:
        defn = event_registry.get(rs)
        if defn:
            assert defn.replay_safety == ReplaySafety.REPLAY_SAFE, f"{rs} must be REPLAY_SAFE"


def test_custom_event_registration():
    custom_reg = EventRegistry()
    entry = EventRegistration(
        event_type="custom.sensor.triggered",
        version="v1",
        description="Triggered when custom sensor detects motion",
        replay_safety=ReplaySafety.REPLAY_SAFE,
        security_class=EventSecurityClass.INTERNAL_OPERATIONAL,
        retention_days=14,
    )
    custom_reg.register(entry)
    fetched = custom_reg.get("custom.sensor.triggered")
    assert fetched is not None
    assert fetched.retention_days == 14
    assert fetched.description == "Triggered when custom sensor detects motion"
