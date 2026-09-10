"""Event normalization, source trust classification, and provenance preservation (Task 60)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.situational_awareness.privacy import situational_privacy_manager
from app.situational_awareness.safety import (
    sanitize_situation_directive,
)
from app.situational_awareness.schemas import (
    EventIngestRequest,
    NormalizedEvent,
    SourceTrustLevel,
)

logger = logging.getLogger(__name__)

# Trusted system sources mapping
_SOURCE_TRUST_MAP = {
    "system": SourceTrustLevel.TRUSTED_SYSTEM,
    "cloudwatch": SourceTrustLevel.TRUSTED_SYSTEM,
    "prometheus": SourceTrustLevel.TRUSTED_SYSTEM,
    "k8s": SourceTrustLevel.TRUSTED_SYSTEM,
    "github_webhook": SourceTrustLevel.VERIFIED_EXTERNAL,
    "datadog": SourceTrustLevel.VERIFIED_EXTERNAL,
    "user_ui": SourceTrustLevel.USER_REPORTED,
    "chat_prompt": SourceTrustLevel.USER_REPORTED,
    "model_agent": SourceTrustLevel.MODEL_GENERATED,
    "simulator": SourceTrustLevel.SIMULATED,
}


class EventNormalizer:
    """Normalizes heterogeneous external/internal events into structured domain events."""

    def normalize(self, req: EventIngestRequest) -> NormalizedEvent:
        """Normalize an incoming event request, sanitizing directives and preserving provenance."""
        # 1. Sanitize text fields to neutralize prompt injections
        clean_subject = sanitize_situation_directive(req.subject)
        clean_event_type = req.event_type.strip().lower()
        clean_env = req.environment.strip().lower()

        # 2. Source trust classification
        source_clean = req.source.strip().lower()
        trust_level = req.source_trust or _SOURCE_TRUST_MAP.get(
            source_clean, SourceTrustLevel.UNVERIFIED_EXTERNAL
        )

        # 3. Timestamp alignment: event time vs ingestion time
        now = datetime.now(timezone.utc)
        occurred = req.occurred_at
        if not occurred:
            occurred = now
        elif not occurred.tzinfo:
            occurred = occurred.replace(tzinfo=timezone.utc)

        # 4. Privacy and secret redaction
        clean_payload = situational_privacy_manager.sanitize_payload(req.payload)

        # 5. Provenance tracking
        provenance = {
            "original_source": req.source,
            "source_trust": trust_level.value,
            "received_at": now.isoformat(),
            "occurred_at": occurred.isoformat(),
            "is_sanitized": True,
        }

        # Confidence based on source trust
        trust_confidence = {
            SourceTrustLevel.TRUSTED_SYSTEM: 1.0,
            SourceTrustLevel.VERIFIED_EXTERNAL: 0.95,
            SourceTrustLevel.USER_REPORTED: 0.70,
            SourceTrustLevel.MODEL_GENERATED: 0.80,
            SourceTrustLevel.SIMULATED: 0.85,
            SourceTrustLevel.UNVERIFIED_EXTERNAL: 0.50,
        }
        conf = trust_confidence.get(trust_level, 0.60)

        normalized = NormalizedEvent(
            event_type=clean_event_type,
            source=req.source,
            source_trust=trust_level,
            environment=clean_env,
            resource=req.resource,
            subject=clean_subject,
            actor=req.actor,
            payload=clean_payload,
            severity=req.severity,
            confidence=conf,
            provenance=provenance,
            occurred_at=occurred,
            received_at=now,
        )

        logger.info(
            "EVENT_NORMALIZED: id=%s type=%s source=%s trust=%s sev=%s",
            normalized.event_id,
            normalized.event_type,
            normalized.source,
            normalized.source_trust.value,
            normalized.severity.value,
        )
        return normalized


event_normalizer = EventNormalizer()
