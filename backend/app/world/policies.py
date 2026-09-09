"""Security, privacy boundaries, anti-surveillance, and anti-injection policies for Kairo World Model (Task 32, Spec 40, 68-72, 111-119)."""

import logging
import re
from typing import Any, Dict, Optional

logger = logging.getLogger("kairo.world.policies")


class WorldAccessDeniedError(PermissionError):
    """Raised when an unauthorized entity or user attempts to query or mutate the World Model."""
    pass


class SurveillanceBoundaryViolationError(ValueError):
    """Raised when an update attempts to inject intrusive surveillance data (e.g., GPS, raw mic/cam streams)."""
    pass


class WorldPolicyEngine:
    """Enforces strict tenant authorization, anti-surveillance limits, and prompt-injection immunity."""

    # Prohibited intrusive metadata keys (Spec 68, 69, 70, 71)
    FORBIDDEN_METADATA_KEYS = {
        "gps_coordinates",
        "latitude",
        "longitude",
        "raw_microphone_audio",
        "raw_camera_stream",
        "raw_screen_recording",
        "eye_tracking",
        "user_presence_video",
        "keystroke_log",
        "facial_recognition",
    }

    # Common prompt injection triggers in external text attempting to forge state (Spec 116)
    INJECTION_STATE_PATTERNS = [
        re.compile(r"ignore\s+(all\s+)?previous\s+instructions", re.IGNORECASE),
        re.compile(r"production\s+is\s+(now\s+)?healthy", re.IGNORECASE),
        re.compile(r"override\s+security\s+status", re.IGNORECASE),
        re.compile(r"set\s+environment\s+to\s+production", re.IGNORECASE),
        re.compile(r"authorize\s+all\s+actions", re.IGNORECASE),
    ]

    @classmethod
    def check_query_permission(
        cls,
        requesting_user_id: str,
        entity_owner_id: str,
        entity_id: str,
    ) -> None:
        """Enforce strict cross-user tenant boundary (Spec 40, 111, 130)."""
        if requesting_user_id != entity_owner_id:
            logger.warning(
                "Cross-user access denied: user '%s' tried to access entity '%s' owned by '%s'",
                requesting_user_id,
                entity_id,
                entity_owner_id,
            )
            raise WorldAccessDeniedError(
                f"Access denied: you do not have permission to view or query entity '{entity_id}'."
            )

    @classmethod
    def sanitize_entity_metadata(cls, metadata: dict[str, Any]) -> dict[str, Any]:
        """Verify and strip intrusive surveillance attributes (Spec 68-72)."""
        clean: dict[str, Any] = {}
        for k, v in metadata.items():
            lower_k = k.lower().strip()
            if lower_k in cls.FORBIDDEN_METADATA_KEYS:
                logger.warning("Surveillance boundary triggered: stripped forbidden metadata key '%s'", k)
                raise SurveillanceBoundaryViolationError(
                    f"Surveillance boundary violation: '{k}' is prohibited in Kairo World Model (Spec 68-71)."
                )
            clean[k] = v
        return clean

    @classmethod
    def validate_external_observation_content(cls, raw_content: str) -> tuple[bool, str]:
        """
        Detect prompt injection in external files (e.g. README claiming 'Production is healthy') (Spec 116).
        Returns (is_clean, sanitized_or_flagged_text).
        """
        for pattern in cls.INJECTION_STATE_PATTERNS:
            if pattern.search(raw_content):
                logger.warning("Prompt injection detected in external observation: %s", raw_content[:80])
                return False, f"[REDACTED_UNTRUSTED_CONTENT: Prompt injection pattern detected]"
        return True, raw_content
