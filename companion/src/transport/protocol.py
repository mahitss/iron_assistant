"""Structured command protocol, expiration watchdog, and idempotency deduplication."""

import logging
import time
from typing import Any

logger = logging.getLogger("kairo.companion.transport.protocol")


class CommandProtocolValidator:
    """Validates structured commands, checks 30-second TTL, and deduplicates replay attacks."""

    DEFAULT_TTL_SECONDS = 30.0

    def __init__(self, ttl_seconds: float = DEFAULT_TTL_SECONDS) -> None:
        self.ttl_seconds = ttl_seconds
        self._seen_command_ids: dict[str, float] = {}  # command_id -> expiry_time
        self._last_sequence = -1

    def _purge_expired_seen(self) -> None:
        """Prune old seen command IDs."""
        now = time.time()
        self._seen_command_ids = {cid: exp for cid, exp in self._seen_command_ids.items() if exp > now}

    def validate_command(self, command: dict[str, Any], target_device_id: str) -> dict[str, Any]:
        """Validate command schema, device targeting, freshness, and idempotency."""
        self._purge_expired_seen()

        # 1. Required fields
        required = ["command_id", "device_id", "action"]
        for field in required:
            if field not in command or not command[field]:
                raise ValueError(f"Invalid command frame: missing mandatory field '{field}'.")

        command_id = str(command["command_id"]).strip()
        device_id = str(command["device_id"]).strip()
        action = str(command["action"]).strip()

        # 2. Strict target device verification
        if device_id != target_device_id:
            raise PermissionError(
                f"Command device_id '{device_id}' does not match local device '{target_device_id}'."
            )

        # 3. Check for replay/duplicate command_id (Idempotency)
        if command_id in self._seen_command_ids:
            raise ValueError(
                f"Duplicate command rejected: command_id '{command_id}' has already been processed."
            )

        # 4. Command Expiration Check (TTL)
        now = time.time()
        cmd_time = command.get("timestamp")
        if cmd_time is not None:
            try:
                # If command timestamp is older than TTL, reject as stale
                age = now - float(cmd_time)
                if age > self.ttl_seconds:
                    raise TimeoutError(
                        f"Command '{command_id}' expired ({age:.1f}s old > max TTL {self.ttl_seconds}s). Discarding stale command."
                    )
                if age < -10.0:
                    raise ValueError(f"Command '{command_id}' has invalid future timestamp.")
            except (ValueError, TypeError) as exc:
                if isinstance(exc, (TimeoutError, ValueError)):
                    raise
                logger.warning("Unparseable command timestamp, treating as current: %s", cmd_time)

        # 5. Sequence Ordering Check (if sequence is specified)
        sequence = command.get("sequence")
        if sequence is not None and isinstance(sequence, int):
            if sequence <= self._last_sequence:
                raise ValueError(
                    f"Out-of-order command '{command_id}': sequence {sequence} <= last sequence {self._last_sequence}."
                )
            self._last_sequence = sequence

        # Record command ID with retention
        self._seen_command_ids[command_id] = now + self.ttl_seconds * 2

        return {
            "command_id": command_id,
            "device_id": device_id,
            "action": action,
            "parameters": command.get("parameters", {}),
            "authorization_context": command.get("authorization_context"),
            "sequence": sequence,
            "validated_at": now,
        }
