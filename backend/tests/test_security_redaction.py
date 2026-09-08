"""Unit tests for ArgumentSanitizer, secret masking, and action fingerprinting."""

from app.security.redaction import ArgumentSanitizer


def test_argument_sanitizer_masks_sensitive_keys():
    """Verify passwords, tokens, API keys, and credentials are obfuscated."""
    args = {
        "repo": "kairo",
        "password": "super_secret_password_123",
        "api_key": "sk-abcdef1234567890abcdef123456",
        "nested": {
            "token": "ghp_12345678901234567890",
            "safe_param": "hello_world",
        },
    }
    sanitized = ArgumentSanitizer.sanitize(args)

    assert sanitized["repo"] == "kairo"
    assert sanitized["password"] == "[REDACTED]"
    assert sanitized["api_key"] == "[REDACTED]"
    assert sanitized["nested"]["token"] == "[REDACTED]"
    assert sanitized["nested"]["safe_param"] == "hello_world"


def test_argument_sanitizer_masks_inline_secret_strings():
    """Verify inline secrets in string values are redacted."""
    raw_text = "Use Bearer secret_bearer_token_value_here to access the API"
    masked = ArgumentSanitizer.redact_string(raw_text)
    assert "[REDACTED_SECRET]" in masked
    assert "secret_bearer_token_value_here" not in masked


def test_argument_sanitizer_truncates_long_strings():
    """Verify oversized strings are bounded to MAX_VALUE_LENGTH."""
    long_str = "A" * 1000
    truncated = ArgumentSanitizer.redact_string(long_str)
    assert len(truncated) <= 550
    assert "[TRUNCATED]" in truncated


def test_action_fingerprint_deterministic_and_unique():
    """Verify fingerprint is deterministic for identical inputs, but sensitive to changes."""
    fp1 = ArgumentSanitizer.compute_action_fingerprint(
        tool_name="git_push",
        user_id="alice",
        session_id="sess_1",
        arguments={"branch": "main", "force": False},
    )
    fp2 = ArgumentSanitizer.compute_action_fingerprint(
        tool_name="git_push",
        user_id="alice",
        session_id="sess_1",
        arguments={"branch": "main", "force": False},
    )
    # Different argument -> different fingerprint!
    fp3 = ArgumentSanitizer.compute_action_fingerprint(
        tool_name="git_push",
        user_id="alice",
        session_id="sess_1",
        arguments={"branch": "main", "force": True},
    )
    # Different user -> different fingerprint!
    fp4 = ArgumentSanitizer.compute_action_fingerprint(
        tool_name="git_push",
        user_id="bob",
        session_id="sess_1",
        arguments={"branch": "main", "force": False},
    )

    assert fp1 == fp2
    assert fp1 != fp3
    assert fp1 != fp4
