"""Tests for secret redaction, log injection prevention, and prompt privacy (Task 38)."""

import json
import logging

from app.observability.logs import StructuredJsonFormatter
from app.observability.sanitization import TelemetrySanitizer


def test_telemetry_sanitizer_redacts_tokens_keys_and_passwords():
    """Sanitizer scrubs OpenAI/GitHub API keys, bearer tokens, passwords, and JWTs."""
    raw_text = (
        "Authorization: Bearer my_super_secret_token_123456789\n"
        "Key: sk-ant-api03-abcdef12345678901234567890\n"
        "GitHub: ghp_123456789012345678901234567890123456\n"
        "Config: password='ultra_secure_password'"
    )
    cleaned = TelemetrySanitizer.sanitize_text(raw_text)

    assert "Bearer my_super_secret_token" not in cleaned
    assert "[REDACTED_SECRET]" in cleaned
    assert "sk-ant-api03" not in cleaned
    assert "ghp_" not in cleaned
    assert "ultra_secure_password" not in cleaned


def test_telemetry_sanitizer_scrubs_sensitive_dictionary_keys():
    """Sanitizer redacts values for keys like password, api_key, cookie, secret."""
    raw_dict = {
        "user": "alice",
        "api_key": "sk-1234567890123456",
        "cookie": "session_id=abcdef123456789",
        "nested": {
            "password": "secret_password",
            "normal_field": "safe_value",
        },
    }
    sanitized = TelemetrySanitizer.sanitize_dict(raw_dict)

    assert sanitized["user"] == "alice"
    assert sanitized["api_key"] == "[REDACTED]"
    assert sanitized["cookie"] == "[REDACTED]"
    assert sanitized["nested"]["password"] == "[REDACTED]"
    assert sanitized["nested"]["normal_field"] == "safe_value"


def test_log_injection_defense_escapes_newlines_and_carriage_returns():
    """Sanitizer escapes newlines to prevent forged log entries via user input."""
    malicious_input = "Normal message\nCRITICAL: [FORGED] Security perimeter breached!\r\n2026-09-10T12:00:00 [FORGED_EVENT]"
    safe_log = TelemetrySanitizer.sanitize_log_message(malicious_input)

    assert "\n" not in safe_log
    assert "\r" not in safe_log
    assert "\\nCRITICAL:" in safe_log


def test_prompt_privacy_stores_hash_and_token_counts_not_raw_text():
    """Prompt metadata generator produces deterministic SHA256 hashes without storing raw prompt."""
    prompt = "Please analyze the financial balance sheet of customer 12345."
    meta = TelemetrySanitizer.extract_prompt_metadata(prompt)

    assert meta["prompt_hash"] is not None
    assert len(meta["prompt_hash"]) == 16
    assert meta["prompt_chars"] == len(prompt)
    assert meta["estimated_tokens"] > 0
    # Raw prompt content must not be present
    assert "financial" not in str(meta)
    assert "customer" not in str(meta)


def test_structured_json_formatter_produces_clean_json():
    """StructuredJsonFormatter produces valid JSON with trace IDs and scrubs injected credentials."""
    formatter = StructuredJsonFormatter()
    record = logging.LogRecord(
        name="kairo.test",
        level=logging.INFO,
        pathname="test.py",
        lineno=42,
        msg="Executing tool with token sk-123456789012345678\nInjected line",
        args=(),
        exc_info=None,
    )
    record.trace_id = "trc_test_999"
    record.task_id = "task_999"
    record.component = "agent"

    output = formatter.format(record)
    parsed = json.loads(output)

    assert parsed["level"] == "INFO"
    assert parsed["service"] == "kairo"
    assert parsed["trace_id"] == "trc_test_999"
    assert parsed["task_id"] == "task_999"
    assert "sk-123456" not in parsed["message"]
    assert "[REDACTED_SECRET]" in parsed["message"]
    assert "\\nInjected line" in parsed["message"]
