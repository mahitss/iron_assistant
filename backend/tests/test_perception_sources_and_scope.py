"""Tests for Perception Sources, Scope Boundaries, Trust Weighting, and Source Liveness (Task 46)."""

from datetime import datetime, timedelta, timezone
import pytest

from app.perception.sources import (
    PerceptionSource,
    PerceptionSourceScope,
    PrivacyLevel,
    SourceRegistry,
    SourceStatus,
    SourceType,
    SourceUnauthorizedError,
)


def utc_now():
    return datetime.now(timezone.utc)


def test_source_registry_registration_and_retrieval():
    registry = SourceRegistry()
    scope = PerceptionSourceScope(
        allowed_users=["user_1", "user_2"],
        allowed_projects=["proj_alpha"],
        allowed_devices=["dev_macbook"],
    )
    src = registry.register_source(
        source_type=SourceType.DEVICE,
        name="Primary Workstation",
        scope=scope,
        capabilities=["battery", "network", "active_app"],
        reliability=0.95,
        privacy_level=PrivacyLevel.INTERNAL,
    )

    assert src.source_id.startswith("src_device_")
    assert src.name == "Primary Workstation"
    assert src.type == SourceType.DEVICE
    assert src.reliability == 0.95
    assert src.status == SourceStatus.HEALTHY
    assert src.privacy_level == PrivacyLevel.INTERNAL

    fetched = registry.get_source(src.source_id)
    assert fetched is not None
    assert fetched.name == "Primary Workstation"


def test_22_authoritative_source_types():
    all_expected = [
        "DEVICE", "DESKTOP", "APPLICATION", "BROWSER", "FILE_SYSTEM",
        "GIT", "GITHUB", "DEPLOYMENT", "SERVICE", "DATABASE", "API",
        "NETWORK", "NOTIFICATION", "VOICE", "VISION", "CALENDAR",
        "AUTOMATION", "AGENT", "TASK_ENGINE", "WORLD_MODEL", "USER_INPUT", "SYSTEM",
    ]
    for st in all_expected:
        assert SourceType(st) is not None


def test_source_scope_authorization_enforcement():
    scope = PerceptionSourceScope(
        allowed_users=["alice"],
        allowed_projects=["kairo_core"],
        allowed_devices=["macbook_pro"],
        allowed_directories=["/workspace/backend", "C:\\projects\\kairo"],
    )
    src = PerceptionSource(
        source_id="src_test_1",
        type=SourceType.FILE_SYSTEM,
        name="Backend Files",
        scope=scope,
    )

    # Authorized caller
    src.validate_authorization(user_id="alice", project_id="kairo_core", device_id="macbook_pro")

    # Unauthorized user
    with pytest.raises(SourceUnauthorizedError, match="Unauthorized access"):
        src.validate_authorization(user_id="bob", project_id="kairo_core", device_id="macbook_pro")

    # Unauthorized project
    with pytest.raises(SourceUnauthorizedError, match="Unauthorized access"):
        src.validate_authorization(user_id="alice", project_id="secret_project", device_id="macbook_pro")

    # Unauthorized device
    with pytest.raises(SourceUnauthorizedError, match="Unauthorized access"):
        src.validate_authorization(user_id="alice", project_id="kairo_core", device_id="rogue_phone")

    # Path scope checking
    assert src.scope.is_resource_in_scope("/workspace/backend/app/main.py") is True
    assert src.scope.is_resource_in_scope("C:/projects/kairo/backend") is True
    assert src.scope.is_resource_in_scope("/etc/passwd") is False


def test_wildcard_source_scope_authorization():
    wildcard_scope = PerceptionSourceScope(
        allowed_users=["*"],
        allowed_projects=["*"],
        allowed_devices=["*"],
    )
    src = PerceptionSource(
        source_id="src_git",
        type=SourceType.GIT,
        name="Global Git Repo",
        scope=wildcard_scope,
    )
    src.validate_authorization(user_id="any_user", project_id="any_project", device_id="any_device")


def test_source_disabling_marks_state_unavailable():
    """Enforce Spec 170: Disabling a source should mark its state UNKNOWN/UNAVAILABLE; never pretend it remains current."""
    registry = SourceRegistry()
    src = registry.register_source(
        source_type=SourceType.SERVICE,
        name="Payment Gateway Service",
        reliability=0.99,
    )
    assert src.status == SourceStatus.HEALTHY

    ok = registry.disable_source(src.source_id)
    assert ok is True
    assert src.status == SourceStatus.DISABLED

    with pytest.raises(SourceUnauthorizedError, match="is DISABLED"):
        src.validate_authorization(user_id="default_user")


def test_source_heartbeat_and_liveness_recovery():
    registry = SourceRegistry()
    src = registry.register_source(
        source_type=SourceType.DEVICE,
        name="Mobile Companion",
    )
    registry.set_status(src.source_id, SourceStatus.OFFLINE)
    assert src.status == SourceStatus.OFFLINE

    # Heartbeat recovers offline source (Spec 161, 163)
    registry.record_heartbeat(src.source_id)
    assert src.status == SourceStatus.HEALTHY


def test_source_listing_with_filters():
    registry = SourceRegistry()
    s1 = registry.register_source(SourceType.BROWSER, "Browser Tab 1", scope=PerceptionSourceScope(allowed_users=["alice"]))
    s2 = registry.register_source(SourceType.GIT, "Repo Main", scope=PerceptionSourceScope(allowed_users=["alice", "bob"]))
    s3 = registry.register_source(SourceType.BROWSER, "Browser Tab 2", scope=PerceptionSourceScope(allowed_users=["bob"]))

    # Filter by source type
    browser_sources = registry.list_sources(source_type=SourceType.BROWSER)
    assert len(browser_sources) == 2
    assert s2 not in browser_sources

    # Filter by authorized user
    alice_sources = registry.list_sources(user_id="alice")
    assert len(alice_sources) == 2
    assert s3 not in alice_sources
