"""Deterministic failure classification and error sanitization for Kairo resilience."""

import re
from typing import Any
from app.resilience.schemas import (
    Failure,
    FailureCategory,
    FailureSeverity,
    utc_now,
)

# Regex patterns to scrub sensitive data from causes, messages, and stack traces
_SENSITIVE_PATTERNS = [
    (re.compile(r"(Bearer\s+)[A-Za-z0-9_\-\.]{10,}", re.IGNORECASE), r"\1[REDACTED_TOKEN]"),
    (re.compile(r"Bearer\s+[A-Za-z0-9_\-\.]{15,}", re.IGNORECASE), r"Bearer [REDACTED_TOKEN]"),
    (re.compile(r"(sk-[A-Za-z0-9_\-]{15,})", re.IGNORECASE), r"[REDACTED_API_KEY]"),
    (re.compile(r'(api[_-]?key["\']?\s*[:=]\s*["\']?)[A-Za-z0-9_\-\.]{8,}(["\']?)', re.IGNORECASE), r"\1[REDACTED]\2"),
    (re.compile(r'(password["\']?\s*[:=]\s*["\']?)[^"\'\s]{4,}(["\']?)', re.IGNORECASE), r"\1[REDACTED]\2"),
    (re.compile(r'(token["\']?\s*[:=]\s*["\']?)[A-Za-z0-9_\-\.]{8,}(["\']?)', re.IGNORECASE), r"\1[REDACTED]\2"),
    (re.compile(r'(secret["\']?\s*[:=]\s*["\']?)[^"\'\s]{6,}(["\']?)', re.IGNORECASE), r"\1[REDACTED]\2"),
    (re.compile(r'(authorization["\']?\s*[:=]\s*["\']?)[^"\'\s]{8,}(["\']?)', re.IGNORECASE), r"\1[REDACTED]\2"),
    (re.compile(r'(cookie["\']?\s*[:=]\s*["\']?)[^"\'\s]{8,}(["\']?)', re.IGNORECASE), r"\1[REDACTED]\2"),
    (re.compile(r"(?:postgresql|postgres|mysql|redis|mongodb|amqp):\/\/[^\s]+", re.IGNORECASE), r"[REDACTED_DATABASE_URL]"),
    (re.compile(r"(://[^:\s]+:)([^@\s]+)(@)", re.IGNORECASE), r"\1[REDACTED_PASSWORD]\3"),
    (re.compile(r"-----BEGIN [A-Z ]+ PRIVATE KEY-----[\s\S]+?-----END [A-Z ]+ PRIVATE KEY-----", re.IGNORECASE), r"[REDACTED_PRIVATE_KEY]"),
]


class ErrorSanitizer:
    """Sanitizes strings and dict payloads to prevent secret leakage."""

    @staticmethod
    def sanitize_text(text: str | None) -> str:
        if not text:
            return ""
        sanitized = text
        for pattern, replacement in _SENSITIVE_PATTERNS:
            sanitized = pattern.sub(replacement, sanitized)
        return sanitized

    @classmethod
    def sanitize_dict(cls, data: dict[str, Any] | None) -> dict[str, Any]:
        if not data:
            return {}
        result: dict[str, Any] = {}
        for k, v in data.items():
            lower_k = k.lower()
            if any(s in lower_k for s in ("token", "secret", "password", "key", "auth", "cookie", "credential")):
                result[k] = "[REDACTED]"
            elif isinstance(v, str):
                result[k] = cls.sanitize_text(v)
            elif isinstance(v, dict):
                result[k] = cls.sanitize_dict(v)
            elif isinstance(v, list):
                result[k] = [cls.sanitize_dict(item) if isinstance(item, dict) else (cls.sanitize_text(item) if isinstance(item, str) else item) for item in v]
            else:
                result[k] = v
        return result


class FailureClassifier:
    """Classifies exceptions and responses deterministically into Failure descriptors."""

    @staticmethod
    def classify(
        exc_or_error: Exception | str | dict[str, Any],
        operation: str,
        component: str,
        correlation_id: str | None = None,
        is_retry_safe_operation: bool = True,
        status_code: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Failure:
        """Deterministically classifies a failure with sanitization and retryability rules."""
        raw_msg = str(exc_or_error)
        msg_lower = raw_msg.lower()

        category = FailureCategory.UNKNOWN
        severity = FailureSeverity.MEDIUM
        code = "GENERIC_ERROR"

        # 1. HTTP Status Code or Explicit Error Codes
        if status_code is not None:
            if status_code == 400:
                category = FailureCategory.VALIDATION
                severity = FailureSeverity.LOW
                code = "HTTP_400_BAD_REQUEST"
            elif status_code == 401:
                category = FailureCategory.AUTHENTICATION
                severity = FailureSeverity.HIGH
                code = "HTTP_401_UNAUTHORIZED"
            elif status_code == 403:
                category = FailureCategory.AUTHORIZATION
                severity = FailureSeverity.HIGH
                code = "HTTP_403_FORBIDDEN"
            elif status_code == 404:
                category = FailureCategory.VALIDATION
                severity = FailureSeverity.LOW
                code = "HTTP_404_NOT_FOUND"
            elif status_code == 408:
                category = FailureCategory.TIMEOUT
                severity = FailureSeverity.MEDIUM
                code = "HTTP_408_REQUEST_TIMEOUT"
            elif status_code == 409:
                category = FailureCategory.CONFLICT
                severity = FailureSeverity.MEDIUM
                code = "HTTP_409_CONFLICT"
            elif status_code == 422:
                category = FailureCategory.VALIDATION
                severity = FailureSeverity.LOW
                code = "HTTP_422_UNPROCESSABLE_ENTITY"
            elif status_code == 429:
                category = FailureCategory.RATE_LIMITED
                severity = FailureSeverity.MEDIUM
                code = "HTTP_429_RATE_LIMITED"
            elif status_code in (502, 503, 504):
                category = FailureCategory.UNAVAILABLE if status_code != 504 else FailureCategory.TIMEOUT
                severity = FailureSeverity.HIGH
                code = f"HTTP_{status_code}_UNAVAILABLE"
            elif status_code >= 500:
                category = FailureCategory.DEPENDENCY
                severity = FailureSeverity.HIGH
                code = f"HTTP_{status_code}_SERVER_ERROR"

        # 2. Text / Exception Type Pattern Matching (if not set by status code)
        if category == FailureCategory.UNKNOWN:
            exc_type = type(exc_or_error).__name__.lower() if isinstance(exc_or_error, Exception) else ""
            combined_text = f"{exc_type} {msg_lower}"

            if any(t in combined_text for t in ("timeout", "timed out", "deadline exceeded")):
                category = FailureCategory.TIMEOUT
                severity = FailureSeverity.MEDIUM
                code = "TIMEOUT_EXCEEDED"
            elif any(t in combined_text for t in ("rate limit", "too many requests", "quota exceeded", "throttled")):
                category = FailureCategory.RATE_LIMITED
                severity = FailureSeverity.MEDIUM
                code = "RATE_LIMIT_EXCEEDED"
            elif any(t in combined_text for t in ("permission denied", "forbidden", "unauthorized", "access denied", "policy denial", "permissionerror")):
                category = FailureCategory.AUTHORIZATION
                severity = FailureSeverity.HIGH
                code = "AUTHORIZATION_DENIED"
            elif any(t in combined_text for t in ("unauthenticated", "invalid api key", "invalid token", "auth failed")):
                category = FailureCategory.AUTHENTICATION
                severity = FailureSeverity.HIGH
                code = "AUTHENTICATION_FAILED"
            elif any(t in combined_text for t in ("validation error", "invalid argument", "malformed", "schema error")):
                category = FailureCategory.VALIDATION
                severity = FailureSeverity.LOW
                code = "VALIDATION_FAILED"
            elif any(t in combined_text for t in ("connection reset", "connection refused", "broken pipe", "network is unreachable", "dns lookup failed", "transient", "connectionreseterror", "connectionrefusederror", "connectionerror")):
                category = FailureCategory.TRANSIENT
                severity = FailureSeverity.MEDIUM
                code = "NETWORK_TRANSIENT"
            elif any(t in combined_text for t in ("stale", "version mismatch", "etag mismatch", "optimistic lock")):
                category = FailureCategory.STALE_STATE
                severity = FailureSeverity.MEDIUM
                code = "STALE_STATE_DETECTED"
            elif any(t in combined_text for t in ("out of memory", "resource exhausted", "disk full")):
                category = FailureCategory.RESOURCE_EXHAUSTED
                severity = FailureSeverity.CRITICAL
                code = "RESOURCE_EXHAUSTED"
            elif any(t in combined_text for t in ("service unavailable", "dependency failure", "upstream connect error")):
                category = FailureCategory.DEPENDENCY
                severity = FailureSeverity.HIGH
                code = "DEPENDENCY_UNAVAILABLE"
            elif any(t in combined_text for t in ("not found", "does not exist", "unsupported", "invalid target")):
                category = FailureCategory.PERMANENT
                severity = FailureSeverity.MEDIUM
                code = "PERMANENT_ERROR"

        # 3. Deterministic Retryability Enforcement
        # Non-retryable categories: AUTHORIZATION, AUTHENTICATION, VALIDATION, PERMANENT
        # Also, if the operation itself is explicitly NOT retry-safe, retryable is False!
        non_retryable_categories = {
            FailureCategory.AUTHENTICATION,
            FailureCategory.AUTHORIZATION,
            FailureCategory.VALIDATION,
            FailureCategory.PERMANENT,
            FailureCategory.CONFLICT,
        }

        if category in non_retryable_categories:
            retryable = False
        else:
            retryable = is_retry_safe_operation and (category in {
                FailureCategory.TRANSIENT,
                FailureCategory.TIMEOUT,
                FailureCategory.RATE_LIMITED,
                FailureCategory.UNAVAILABLE,
                FailureCategory.DEPENDENCY,
                FailureCategory.RESOURCE_EXHAUSTED,
            })

        sanitized_cause = ErrorSanitizer.sanitize_text(raw_msg)
        sanitized_meta = ErrorSanitizer.sanitize_dict(metadata or {})

        return Failure(
            category=category,
            code=code,
            operation=operation,
            component=component,
            retryable=retryable,
            severity=severity,
            occurred_at=utc_now(),
            correlation_id=correlation_id,
            cause=sanitized_cause,
            metadata=sanitized_meta,
        )
