"""Unit tests for memory content sanitization and basic secret prevention."""

import pytest

from app.memory.sanitizer import MemorySanitizer, UnsafeMemoryError


def test_clean_memory_content_passes():
    """Verify normal, safe memory strings pass validation untouched."""
    text = "User prefers concise technical responses with code snippets."
    result = MemorySanitizer.validate_and_sanitize(text)
    assert result == text
    assert MemorySanitizer.contains_sensitive_data(text) is False


def test_rejects_api_keys():
    """Verify standard secret patterns like OpenAI/OpenRouter keys are rejected."""
    key_text = "My API key is pk_test_sample_token_secret_1234567890abcdef"
    assert MemorySanitizer.contains_sensitive_data(key_text) is True
    with pytest.raises(UnsafeMemoryError, match="sensitive credentials"):
        MemorySanitizer.validate_and_sanitize(key_text, reject_on_secret=True)


def test_rejects_github_tokens():
    """Verify GitHub access tokens are rejected."""
    gh_token = "Use ghp_123456789012345678901234567890123456 for access"
    assert MemorySanitizer.contains_sensitive_data(gh_token) is True
    with pytest.raises(UnsafeMemoryError):
        MemorySanitizer.validate_and_sanitize(gh_token)


def test_rejects_private_keys():
    """Verify PEM format private keys are rejected."""
    pem = "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA0...\n-----END RSA PRIVATE KEY-----"
    assert MemorySanitizer.contains_sensitive_data(pem) is True
    with pytest.raises(UnsafeMemoryError):
        MemorySanitizer.validate_and_sanitize(pem)


def test_rejects_passwords():
    """Verify explicit password assignments are detected and rejected."""
    pwd_text = "The database password: my_super_secret_password_123"
    assert MemorySanitizer.contains_sensitive_data(pwd_text) is True
    with pytest.raises(UnsafeMemoryError):
        MemorySanitizer.validate_and_sanitize(pwd_text)


def test_sanitize_mode_redacts_rather_than_raising():
    """Verify non-rejecting sanitize mode replaces secret with placeholder."""
    mixed_text = "API Key: pk_test_sample_token_secret_1234567890abcdef for project"
    sanitized = MemorySanitizer.sanitize(mixed_text)
    assert "pk_test_" not in sanitized
    assert "[REDACTED_SECRET]" in sanitized
