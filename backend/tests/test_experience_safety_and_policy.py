"""Unit tests for Experience safety, governance guards, anti-profiling, and sanitization (Sections 30, 41, 48, 73, 90)."""

import pytest
from app.experience.safety import (
    ExperienceSecurityGuard,
    ExperienceSecurityViolation,
    ProhibitedProfilingError,
    sanitize_content,
    validate_learning_candidate,
    validate_preference_safety,
)
from app.experience.schemas import ExperienceSource


def test_anti_prompt_injection_external_source_blocked():
    """Section 48: External web content or untrusted source cannot create durable preferences."""
    with pytest.raises(PermissionError) as exc_info:
        validate_preference_safety(
            key="favorite_editor",
            value="VSCode",
            source=ExperienceSource.SYSTEM_OBSERVED,
        )
    assert "not authorized to create durable preferences" in str(exc_info.value)


def test_governance_domain_bypass_blocked():
    """Section 30: Preferences cannot modify security policies, permissions, or approvals."""
    prohibited_keys = [
        "security_center_bypass",
        "disable_permissions",
        "approvals_auto_accept",
        "tool_allowlist_expand",
        "skill_risk_downgrade",
        "auth_tokens_leak",
        "emergency_stop_override",
    ]

    for bad_key in prohibited_keys:
        with pytest.raises(PermissionError) as exc_info:
            validate_preference_safety(
                key=bad_key,
                value="true",
                source=ExperienceSource.USER_EXPLICIT,
            )
        assert "Security Invariance Violation" in str(exc_info.value)


def test_prohibited_sensitive_profiling_blocked():
    """Section 41: Prohibits psychological, political, health, religious, or sexual profiling."""
    prohibited_profiles = [
        ("psychological_trait", "introverted"),
        ("political_affiliation", "neutral"),
        ("religious_belief", "agnostic"),
        ("sexual_orientation", "heterosexual"),
        ("health_status", "diabetic"),
        ("medical_condition", "asthma"),
        ("racial_origin", "caucasian"),
    ]

    for key, val in prohibited_profiles:
        with pytest.raises(ValueError) as exc_info:
            validate_preference_safety(
                key=key,
                value=val,
                source=ExperienceSource.USER_EXPLICIT,
            )
        assert "Privacy Violation" in str(exc_info.value)


def test_learning_candidate_governance_guard():
    """Section 30, 31: Learning candidates cannot target security or permissions."""
    bad_proposals = [
        "Modify SecurityCenter to allow all bash commands",
        "Automatically relax permissions for computer control",
        "Bypass approvals requirements for git push",
        "Expand tool_allowlist without engineering review",
    ]

    for proposal in bad_proposals:
        with pytest.raises(PermissionError) as exc_info:
            validate_learning_candidate(proposal, "GLOBAL")
        assert "Forbidden Learning Proposal" in str(exc_info.value)


def test_safe_task_oriented_preference_allowed():
    """Verify safe task-oriented preferences pass validation."""
    # Should not raise
    validate_preference_safety(
        key="preferred_language",
        value="TypeScript",
        source=ExperienceSource.USER_EXPLICIT,
    )
    validate_preference_safety(
        key="preferred_output_format",
        value="Markdown tables",
        source=ExperienceSource.USER_EXPLICIT,
    )


def test_credential_sanitization():
    """Section 73: Secrets, tokens, and passwords must be redacted from experience payloads."""
    payload = {
        "api_key": "sk-proj-super-secret-key-12345",
        "user_token": "bearer-auth-token-abc",
        "message": "Connected with password secret_pass_99",
        "safe_detail": "Used SQLite for project alpha",
    }
    cleaned = sanitize_content(payload)
    assert cleaned["api_key"] == "[REDACTED]"
    assert cleaned["user_token"] == "[REDACTED]"
    assert cleaned["safe_detail"] == "Used SQLite for project alpha"
