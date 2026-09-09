"""Tests for Privacy Invariants, Anti-Surveillance, Tenant Isolation, Secret Redaction, and Replay (Task 46)."""

from datetime import datetime, timezone
import pytest

from app.perception.events import EventType, PerceptionEvent
from app.perception.privacy import (
    CrossTenantPerceptionError,
    PerceptionPrivacyGuard,
    PrivacyViolationError,
)
from app.perception.redaction import SecretRedactor
from app.perception.service import PerceptionService
from app.perception.sources import PerceptionSource, PerceptionSourceScope, PrivacyLevel, SourceType


def utc_now():
    return datetime.now(timezone.utc)


def test_anti_surveillance_invariants():
    """Enforce Spec 39-42, 197: Screen/Camera/Microphone require explicit authorization; no continuous capture by default."""
    source_cam = PerceptionSource(
        source_id="src_cam_1",
        type=SourceType.VISION,
        name="Workspace Camera",
        scope=PerceptionSourceScope(require_explicit_consent=True),
    )

    # Ingestion attempt without user consent fails
    with pytest.raises(PrivacyViolationError, match="Continuous surveillance is prohibited"):
        PerceptionPrivacyGuard.validate_modal_capture_authorization(
            source=source_cam,
            has_explicit_user_consent=False,
        )

    # Ingestion with explicit consent passes
    PerceptionPrivacyGuard.validate_modal_capture_authorization(
        source=source_cam,
        has_explicit_user_consent=True,
    )


def test_secret_and_credential_redaction():
    """Enforce Spec 48, 52, 177: Redact secrets, passwords, and tokens before persistence or logging."""
    raw_payload = {
        "user": "developer",
        "api_key": "sk-abcdef1234567890abcdef1234567890",
        "db_connection": "postgresql://postgres:super_secret_pw@localhost:5432/kairo_db",
        "nested": {
            "auth_token": "bearer ghp_1234567890abcdef1234567890abcdef",
            "safe_field": "public_data",
        },
        "tags": ["prod", "password=plaintext123"],
    }

    cleaned, was_redacted = SecretRedactor.redact_payload(raw_payload)

    assert was_redacted is True
    assert cleaned["api_key"] == SecretRedactor.REDACTED_MASK
    assert SecretRedactor.REDACTED_MASK in cleaned["db_connection"]
    assert cleaned["nested"]["auth_token"] == SecretRedactor.REDACTED_MASK
    assert cleaned["nested"]["safe_field"] == "public_data"


def test_cross_tenant_isolation_guards():
    """Enforce Spec 178-181: Cross-user, cross-project, and cross-device state isolation."""
    # Cross-user attempt
    with pytest.raises(CrossTenantPerceptionError, match="Access denied: Perception belongs to user 'alice'"):
        PerceptionPrivacyGuard.validate_tenant_isolation(
            source_scope_user="alice",
            source_scope_project="proj_1",
            requesting_user_id="bob",
            requesting_project_id="proj_1",
        )

    # Cross-project attempt
    with pytest.raises(CrossTenantPerceptionError, match="Access denied: Perception belongs to project 'secret_vault'"):
        PerceptionPrivacyGuard.validate_tenant_isolation(
            source_scope_user="alice",
            source_scope_project="secret_vault",
            requesting_user_id="alice",
            requesting_project_id="public_blog",
        )


def test_deterministic_event_replay_without_side_effects():
    """Enforce Spec 166, 167: Deterministic replay for debugging without executing external side effects."""
    service = PerceptionService()
    source = service.sources.register_source(SourceType.DEVICE, "Laptop Device")

    test_events = [
        {"action": "STATUS_CHANGED", "device_id": "laptop_1", "battery_level": 90, "is_online": True},
        {"action": "STATUS_CHANGED", "device_id": "laptop_1", "battery_level": 89, "is_online": True},
    ]

    replayed = service.replay_events(test_events, source)
    assert len(replayed) == 2
    assert replayed[0].subject == "device:laptop_1"
    assert replayed[0].data["battery_level"] == 90
    assert replayed[1].data["battery_level"] == 89
