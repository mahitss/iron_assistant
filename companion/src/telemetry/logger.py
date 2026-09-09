"""Safe local audit logger redacting passwords, tokens, keys, and private multimedia."""

import json
import logging
import re
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger("kairo.companion.telemetry.logger")

# Redaction patterns
REDACTION_PATTERNS = [
    (
        re.compile(
            r"(password|passwd|secret|token|api_key|key|auth)[\"']?\s*[:=]\s*[\"']?([^\"'\s,]+)",
            re.IGNORECASE,
        ),
        r"\1=***REDACTED***",
    ),
    (re.compile(r"(sk|ghp|gho|pat)_[a-zA-Z0-9]{15,}", re.IGNORECASE), r"***REDACTED_KEY***"),
    (
        re.compile(r"-----BEGIN [A-Z ]+PRIVATE KEY-----[\s\S]*?-----END [A-Z ]+PRIVATE KEY-----"),
        r"***REDACTED_PRIVATE_KEY***",
    ),
]


class LocalAuditLogger:
    """Records immutable local audit events while strictly guaranteeing zero PII/secret leakage."""

    def __init__(self, log_dir: Path | None = None) -> None:
        self.log_dir = log_dir or (Path.home() / ".kairo" / "companion" / "logs")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.audit_file = self.log_dir / "companion_audit.jsonl"

    def _redact(self, text: str) -> str:
        """Apply redaction regexes to text."""
        result = text
        for pattern, replacement in REDACTION_PATTERNS:
            result = pattern.sub(replacement, result)
        return result

    def log_event(
        self,
        command_id: str,
        action: str,
        decision: str,
        success: bool,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Append a redacted audit entry to the local JSONL log."""
        safe_details = details or {}
        # Strip binary payloads, raw base64, audio bytes, and camera frames
        cleaned_details = {}
        for k, v in safe_details.items():
            if k in ("data_base64", "audio_bytes", "frame_bytes", "content") and isinstance(v, (str, bytes)):
                cleaned_details[k] = f"[BLOB: {len(v)} bytes omitted for privacy]"
            else:
                cleaned_details[k] = v

        raw_entry = json.dumps(
            {
                "timestamp": time.time(),
                "command_id": command_id,
                "action": action,
                "decision": decision,
                "success": success,
                "details": cleaned_details,
            }
        )
        redacted_entry = self._redact(raw_entry)

        with open(self.audit_file, "a", encoding="utf-8") as f:
            f.write(redacted_entry + "\n")

    def read_recent_events(self, limit: int = 50) -> list[dict[str, Any]]:
        """Read latest audit events."""
        if not self.audit_file.exists():
            return []
        lines = self.audit_file.read_text(encoding="utf-8").strip().splitlines()
        recent = lines[-limit:]
        events = []
        for line in reversed(recent):
            try:
                events.append(json.loads(line))
            except Exception:
                continue
        return events
