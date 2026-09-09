"""Telemetry secret redaction, log injection defense, and prompt sanitization (Task 38)."""

import hashlib
import re
from typing import Any

# Regular expressions for sensitive tokens, API keys, and authorization headers
_RE_BEARER = re.compile(r"(Bearer\s+)[A-Za-z0-9_\-\.]{12,}", re.IGNORECASE)
_RE_API_KEY = re.compile(r"(sk-[a-zA-Z0-9_\-]{15,}|ghp_[a-zA-Z0-9]{20,}|key-[a-zA-Z0-9]{16,})")
_RE_JWT = re.compile(r"eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}")
_RE_GENERIC_SECRET = re.compile(r"(password|secret|token|apikey|api_key|access_token|private_key)\s*[:=]\s*['\"]?([^'\"\s,]{6,})['\"]?", re.IGNORECASE)

_SENSITIVE_DICT_KEYS = {
    "password",
    "secret",
    "token",
    "api_key",
    "apikey",
    "access_token",
    "refresh_token",
    "private_key",
    "authorization",
    "cookie",
    "credentials",
    "session_secret",
}


class TelemetrySanitizer:
    """Provides high-performance, deterministic sanitization for logs, traces, and metrics."""

    @classmethod
    def sanitize_text(cls, text: str | None) -> str:
        """Removes sensitive credentials, API keys, and tokens from a text string."""
        if not text:
            return ""

        # 1. Redact Bearer tokens
        sanitized = _RE_BEARER.sub(r"\1[REDACTED_SECRET]", text)

        # 2. Redact specific API keys (OpenAI, GitHub, etc.)
        sanitized = _RE_API_KEY.sub("[REDACTED_SECRET]", sanitized)

        # 3. Redact JWTs
        sanitized = _RE_JWT.sub("[REDACTED_SECRET]", sanitized)

        # 4. Redact key-value secrets (e.g. password=xyz)
        sanitized = _RE_GENERIC_SECRET.sub(r"\1=[REDACTED_SECRET]", sanitized)

        return sanitized

    @classmethod
    def sanitize_dict(cls, data: dict[str, Any] | None, max_string_len: int = 2048) -> dict[str, Any]:
        """Recursively sanitizes dictionary payloads, stripping secret keys and truncating strings."""
        if not data:
            return {}

        result: dict[str, Any] = {}
        for key, value in data.items():
            key_str = str(key)
            lower_key = key_str.lower()

            if any(sens in lower_key for sens in _SENSITIVE_DICT_KEYS):
                result[key_str] = "[REDACTED]"
            elif isinstance(value, dict):
                result[key_str] = cls.sanitize_dict(value, max_string_len=max_string_len)
            elif isinstance(value, list):
                result[key_str] = [
                    cls.sanitize_dict(item, max_string_len=max_string_len)
                    if isinstance(item, dict)
                    else (cls.sanitize_text(str(item))[:max_string_len] if isinstance(item, str) else item)
                    for item in value
                ]
            elif isinstance(value, str):
                cleaned = cls.sanitize_text(value)
                if len(cleaned) > max_string_len:
                    cleaned = cleaned[:max_string_len] + f"... [truncated {len(cleaned) - max_string_len} chars]"
                result[key_str] = cleaned
            else:
                result[key_str] = value

        return result

    @classmethod
    def sanitize_log_message(cls, message: str) -> str:
        """Sanitizes text and escapes carriage returns/newlines to prevent log injection."""
        sanitized = cls.sanitize_text(message)
        # Escape newlines and control characters to prevent log forgery
        return sanitized.replace("\r", "\\r").replace("\n", "\\n")

    @classmethod
    def extract_prompt_metadata(cls, prompt: str | None) -> dict[str, Any]:
        """Extracts privacy-safe prompt metadata (hash and token count) without storing raw prompt."""
        if not prompt:
            return {"prompt_hash": None, "prompt_chars": 0, "estimated_tokens": 0}

        prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:16]
        chars = len(prompt)
        # Bounded token estimation (~4 chars per token)
        est_tokens = max(1, chars // 4)

        return {
            "prompt_hash": prompt_hash,
            "prompt_chars": chars,
            "estimated_tokens": est_tokens,
        }

    @classmethod
    def sanitize_tool_args(cls, args: dict[str, Any] | None) -> dict[str, Any]:
        """Sanitizes tool arguments, redacting credentials and large document contents."""
        return cls.sanitize_dict(args, max_string_len=512)

    @classmethod
    def sanitize_tool_result(cls, result: Any) -> dict[str, Any]:
        """Summarizes tool execution results safely for telemetry."""
        if result is None:
            return {"status": "none", "summary": "None"}

        if isinstance(result, dict):
            sanitized = cls.sanitize_dict(result, max_string_len=512)
            return {"status": "ok", "type": "dict", "keys": list(sanitized.keys())[:10], "preview": sanitized}

        if isinstance(result, str):
            cleaned = cls.sanitize_text(result)
            return {
                "status": "ok",
                "type": "str",
                "length": len(result),
                "summary": cleaned[:256] + ("..." if len(cleaned) > 256 else ""),
            }

        return {"status": "ok", "type": type(result).__name__, "summary": str(result)[:128]}
