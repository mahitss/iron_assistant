"""Canonical failure taxonomy and deterministic error classification for Kairo Reliability (Task 88)."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
import re
from typing import Any
import uuid

# ==============================================================================
# 1. CANONICAL FAILURE TAXONOMY
# ==============================================================================

class FailureType(str, Enum):
    """Canonical typed failure taxonomy across Python Brain and Rust Body."""

    PROCESS_FAILURE = "PROCESS_FAILURE"
    RUNTIME_FAILURE = "RUNTIME_FAILURE"
    IPC_FAILURE = "IPC_FAILURE"
    PROTOCOL_FAILURE = "PROTOCOL_FAILURE"
    SANDBOX_FAILURE = "SANDBOX_FAILURE"
    RESOURCE_FAILURE = "RESOURCE_FAILURE"
    MEMORY_PRESSURE = "MEMORY_PRESSURE"
    CPU_PRESSURE = "CPU_PRESSURE"
    DISK_PRESSURE = "DISK_PRESSURE"
    NETWORK_FAILURE = "NETWORK_FAILURE"
    DNS_FAILURE = "DNS_FAILURE"
    TLS_FAILURE = "TLS_FAILURE"
    TOOL_FAILURE = "TOOL_FAILURE"
    COMPUTER_FAILURE = "COMPUTER_FAILURE"
    WORKFLOW_FAILURE = "WORKFLOW_FAILURE"
    DATABASE_FAILURE = "DATABASE_FAILURE"
    REDIS_FAILURE = "REDIS_FAILURE"
    DEPENDENCY_FAILURE = "DEPENDENCY_FAILURE"
    TIMEOUT = "TIMEOUT"
    DEADLINE_EXCEEDED = "DEADLINE_EXCEEDED"
    CANCELLATION = "CANCELLATION"
    AUTHORIZATION_FAILURE = "AUTHORIZATION_FAILURE"
    GOVERNANCE_FAILURE = "GOVERNANCE_FAILURE"
    APPROVAL_FAILURE = "APPROVAL_FAILURE"
    VERIFICATION_FAILURE = "VERIFICATION_FAILURE"
    CONFIGURATION_FAILURE = "CONFIGURATION_FAILURE"
    CORRUPTION = "CORRUPTION"
    UNKNOWN_FAILURE = "UNKNOWN_FAILURE"


class FailureSeverity(str, Enum):
    """Deterministic failure severity levels."""

    P0 = "P0"  # Catastrophic: host/core security, corruption, uncontainable crash loops
    P1 = "P1"  # Critical: runtime daemon crash, database outage, sandbox failure
    P2 = "P2"  # Major: network outage, tool execution abort, resource exhaustion
    P3 = "P3"  # Minor: recoverable timeouts, rate limiting, retryable IPC glitches
    P4 = "P4"  # Diagnostic: warnings, non-critical telemetry drops, config drift notices

    @property
    def rank(self) -> int:
        """Numeric rank for sorting (P0 is highest priority)."""
        mapping = {"P0": 0, "P1": 1, "P2": 2, "P3": 3, "P4": 4}
        return mapping.get(self.value, 5)


# ==============================================================================
# 2. SENSITIVE TOKEN SANITIZATION
# ==============================================================================

_REDACTION_PATTERNS = [
    (re.compile(r"(Bearer\s+)[A-Za-z0-9_\-\.]{10,}", re.IGNORECASE), r"\1[REDACTED_TOKEN]"),
    (re.compile(r"(sk-[A-Za-z0-9_\-]{15,})", re.IGNORECASE), r"[REDACTED_API_KEY]"),
    (re.compile(r'(api[_-]?key["\']?\s*[:=]\s*["\']?)[A-Za-z0-9_\-\.]{8,}(["\']?)', re.IGNORECASE), r"\1[REDACTED]\2"),
    (re.compile(r'(password["\']?\s*[:=]\s*["\']?)[^"\'\s]{4,}(["\']?)', re.IGNORECASE), r"\1[REDACTED]\2"),
    (re.compile(r'(secret["\']?\s*[:=]\s*["\']?)[^"\'\s]{6,}(["\']?)', re.IGNORECASE), r"\1[REDACTED]\2"),
    (re.compile(r"(?:postgresql|postgres|mysql|redis|mongodb|amqp):\/\/[^\s]+", re.IGNORECASE), r"[REDACTED_DATABASE_URL]"),
    (re.compile(r"-----BEGIN [A-Z ]+ PRIVATE KEY-----[\s\S]+?-----END [A-Z ]+ PRIVATE KEY-----", re.IGNORECASE), r"[REDACTED_PRIVATE_KEY]"),
]


def sanitize_message(msg: str | None) -> str:
    """Sanitize arbitrary strings to guarantee zero secret or token leaks."""
    if not msg:
        return ""
    sanitized = str(msg)
    for pattern, replacement in _REDACTION_PATTERNS:
        sanitized = pattern.sub(replacement, sanitized)
    return sanitized


def sanitize_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    """Recursively sanitize dictionary payloads."""
    if not payload:
        return {}
    res: dict[str, Any] = {}
    for k, v in payload.items():
        lower_k = str(k).lower()
        if any(s in lower_k for s in ("token", "secret", "password", "key", "auth", "credential")):
            res[k] = "[REDACTED]"
        elif isinstance(v, str):
            res[k] = sanitize_message(v)
        elif isinstance(v, dict):
            res[k] = sanitize_payload(v)
        elif isinstance(v, list):
            res[k] = [sanitize_payload(i) if isinstance(i, dict) else (sanitize_message(i) if isinstance(i, str) else i) for i in v]
        else:
            res[k] = v
    return res


# ==============================================================================
# 3. DETERMINISTIC FAILURE CLASSIFIER
# ==============================================================================

class FailureClassifier:
    """Classifies exceptions, error codes, and telemetry facts into canonical failure records."""

    @staticmethod
    def classify(
        exc_or_error: Exception | str | dict[str, Any],
        component: str,
        operation: str = "unspecified",
        correlation_id: str | None = None,
        trace_id: str | None = None,
        causation_id: str | None = None,
        status_code: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Deterministically map inputs to typed failure fields."""
        raw_msg = str(exc_or_error)
        msg_lower = raw_msg.lower()
        exc_type = type(exc_or_error).__name__.lower() if isinstance(exc_or_error, Exception) else ""
        combined = f"{exc_type} {msg_lower}"

        failure_type = FailureType.UNKNOWN_FAILURE
        severity = FailureSeverity.P2
        recoverable = True
        retryable = False

        # 1. Status Code Rules
        if status_code is not None:
            if status_code == 401 or status_code == 403:
                failure_type = FailureType.AUTHORIZATION_FAILURE
                severity = FailureSeverity.P1
                recoverable = False
                retryable = False
            elif status_code == 408 or status_code == 504:
                failure_type = FailureType.TIMEOUT
                severity = FailureSeverity.P3
                recoverable = True
                retryable = True
            elif status_code == 429:
                failure_type = FailureType.RESOURCE_FAILURE
                severity = FailureSeverity.P3
                recoverable = True
                retryable = True
            elif status_code in (502, 503):
                failure_type = FailureType.DEPENDENCY_FAILURE
                severity = FailureSeverity.P2
                recoverable = True
                retryable = True

        # 2. Text / Type Pattern Rules (if not matched by status code)
        if failure_type == FailureType.UNKNOWN_FAILURE:
            if any(k in combined for k in ("sigkill", "segmentation fault", "segv", "signal", "process exited", "process terminated", "crash")):
                failure_type = FailureType.PROCESS_FAILURE
                severity = FailureSeverity.P1
                recoverable = True
                retryable = False
            elif any(k in combined for k in ("connection reset", "connectionreset", "broken pipe", "brokenpipe", "connection refused", "ipc", "socket closed", "socket reset")):
                failure_type = FailureType.IPC_FAILURE
                severity = FailureSeverity.P2
                recoverable = True
                retryable = True
            elif any(k in combined for k in ("protocol", "session invalid", "malformed envelope", "version mismatch")):
                failure_type = FailureType.PROTOCOL_FAILURE
                severity = FailureSeverity.P2
                recoverable = True
                retryable = False
            elif any(k in combined for k in ("sandbox", "mmu", "job object", "path traversal", "security boundary")):
                failure_type = FailureType.SANDBOX_FAILURE
                severity = FailureSeverity.P1
                recoverable = True
                retryable = False
            elif any(k in combined for k in ("out of memory", "oom", "memory limit", "memory pressure")):
                failure_type = FailureType.MEMORY_PRESSURE
                severity = FailureSeverity.P1
                recoverable = True
                retryable = False
            elif any(k in combined for k in ("cpu limit", "cpu rate", "cpu pressure")):
                failure_type = FailureType.CPU_PRESSURE
                severity = FailureSeverity.P2
                recoverable = True
                retryable = False
            elif any(k in combined for k in ("disk full", "disk limit", "no space left")):
                failure_type = FailureType.DISK_PRESSURE
                severity = FailureSeverity.P1
                recoverable = True
                retryable = False
            elif any(k in combined for k in ("dns", "resolve", "name resolution")):
                failure_type = FailureType.DNS_FAILURE
                severity = FailureSeverity.P2
                recoverable = True
                retryable = True
            elif any(k in combined for k in ("tls", "ssl", "certificate", "handshake failure")):
                failure_type = FailureType.TLS_FAILURE
                severity = FailureSeverity.P2
                recoverable = True
                retryable = False
            elif any(k in combined for k in ("network", "http fetch", "ssrf", "connection error")):
                failure_type = FailureType.NETWORK_FAILURE
                severity = FailureSeverity.P2
                recoverable = True
                retryable = True
            elif any(k in combined for k in ("window", "display", "clipboard", "mouse", "keyboard", "screen capture")):
                failure_type = FailureType.COMPUTER_FAILURE
                severity = FailureSeverity.P2
                recoverable = True
                retryable = False
            elif any(k in combined for k in ("tool", "tool execution", "unsupported tool", "tool failure")):
                failure_type = FailureType.TOOL_FAILURE
                severity = FailureSeverity.P2
                recoverable = True
                retryable = False
            elif any(k in combined for k in ("workflow", "step failed", "dag execution")):
                failure_type = FailureType.WORKFLOW_FAILURE
                severity = FailureSeverity.P2
                recoverable = True
                retryable = False
            elif any(k in combined for k in ("database", "postgres", "sqlite", "sqlalchemy", "operationalerror")):
                failure_type = FailureType.DATABASE_FAILURE
                severity = FailureSeverity.P1
                recoverable = True
                retryable = False
            elif any(k in combined for k in ("redis", "aioredis")):
                failure_type = FailureType.REDIS_FAILURE
                severity = FailureSeverity.P2
                recoverable = True
                retryable = True
            elif any(k in combined for k in ("timeout", "timed out", "asyncio.timeouterror")):
                failure_type = FailureType.TIMEOUT
                severity = FailureSeverity.P3
                recoverable = True
                retryable = True
            elif any(k in combined for k in ("deadline exceeded", "deadline")):
                failure_type = FailureType.DEADLINE_EXCEEDED
                severity = FailureSeverity.P2
                recoverable = True
                retryable = False
            elif any(k in combined for k in ("cancelled", "cancellation", "task cancelled")):
                failure_type = FailureType.CANCELLATION
                severity = FailureSeverity.P3
                recoverable = True
                retryable = False
            elif any(k in combined for k in ("permission denied", "forbidden", "unauthorized", "policy denial")):
                failure_type = FailureType.AUTHORIZATION_FAILURE
                severity = FailureSeverity.P1
                recoverable = False
                retryable = False
            elif any(k in combined for k in ("governance", "constitutional", "authority")):
                failure_type = FailureType.GOVERNANCE_FAILURE
                severity = FailureSeverity.P1
                recoverable = False
                retryable = False
            elif any(k in combined for k in ("approval required", "approval rejected", "approval")):
                failure_type = FailureType.APPROVAL_FAILURE
                severity = FailureSeverity.P2
                recoverable = False
                retryable = False
            elif any(k in combined for k in ("verification failed", "verification")):
                failure_type = FailureType.VERIFICATION_FAILURE
                severity = FailureSeverity.P2
                recoverable = True
                retryable = False
            elif any(k in combined for k in ("config", "configuration", "fingerprint mismatch")):
                failure_type = FailureType.CONFIGURATION_FAILURE
                severity = FailureSeverity.P3
                recoverable = True
                retryable = False
            elif any(k in combined for k in ("corruption", "corrupted", "checksum mismatch")):
                failure_type = FailureType.CORRUPTION
                severity = FailureSeverity.P0
                recoverable = False
                retryable = False

        # Component Criticality Overrides
        if component.lower() in ("security_center", "emergency_stop", "policy_engine"):
            severity = FailureSeverity.P0
        elif component.lower() in ("native_runtime", "database", "sqlite", "postgres") and severity.rank > 1:
            severity = FailureSeverity.P1

        sanitized_msg = sanitize_message(raw_msg)
        sanitized_meta = sanitize_payload(metadata or {})

        return {
            "failure_id": f"fail_{uuid.uuid4().hex[:12]}",
            "failure_type": failure_type,
            "component": component,
            "operation": operation,
            "severity": severity,
            "timestamp": datetime.now(timezone.utc),
            "correlation_id": correlation_id or "unspecified",
            "trace_id": trace_id,
            "causation_id": causation_id,
            "root_cause_candidate": component,
            "affected_resources": sanitized_meta.get("resources", []),
            "affected_executions": sanitized_meta.get("executions", []),
            "confidence": 0.9 if failure_type != FailureType.UNKNOWN_FAILURE else 0.5,
            "recoverability": recoverable,
            "retryability": retryable,
            "message": sanitized_msg,
            "metadata": sanitized_meta,
        }
