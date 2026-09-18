"""Normalization Engine for Task 111:
Projects canonical events into the unified multi-clock temporal domain.

Strict Invariants:
- EVENT != STATE != CAUSE
- EVENT TIME != INGESTION TIME
- UNTRUSTED EVENT PAYLOAD CANNOT ELEVATE AUTHORITY
"""

from __future__ import annotations

from datetime import UTC, datetime
import re
from typing import Any, Dict, Optional

from app.temporal.domain import (
    MultiClockTimestamps,
    TemporalEvent,
    gen_temporal_id,
    utc_now,
)


class NormalizationEngine:
    """Normalizes heterogenous Kairo events into typed TemporalEvents with distinct clocks."""

    CATEGORY_MAPPINGS: Dict[str, str] = {
        "action": "ACTION",
        "decision": "DECISION",
        "mission": "MISSION",
        "goal": "GOAL",
        "world": "WORLD_STATE",
        "belief": "BELIEF",
        "memory": "MEMORY",
        "attention": "ATTENTION",
        "situation": "SITUATION",
        "capability": "CAPABILITY",
        "resource": "RESOURCE",
        "runtime": "RUNTIME",
        "security": "SECURITY",
        "governance": "GOVERNANCE",
        "recovery": "RECOVERY",
        "evaluation": "EVALUATION",
        "user": "USER",
        "chat": "CONVERSATION",
    }

    @classmethod
    def normalize(
        cls,
        event_dict_or_obj: Any,
        ingested_at: Optional[datetime] = None,
        observed_at: Optional[datetime] = None,
        effective_at: Optional[datetime] = None,
        sequence_num: int = 0,
        monotonic_ts: float = 0.0,
    ) -> TemporalEvent:
        """Projects a raw event dictionary or canonical Event model into a TemporalEvent."""
        now = utc_now()
        ingested_time = ingested_at or now
        processed_time = now

        # Extract attributes handling both dict and BaseModel
        if hasattr(event_dict_or_obj, "model_dump"):
            raw = event_dict_or_obj.model_dump()
        elif isinstance(event_dict_or_obj, dict):
            raw = event_dict_or_obj
        else:
            raw = getattr(event_dict_or_obj, "__dict__", {})

        canonical_id = str(raw.get("event_id") or raw.get("id") or gen_temporal_id("evt"))
        event_type = str(raw.get("event_type") or "system.generic")
        source = str(raw.get("source") or "system")

        # Parse event timestamp (when it actually occurred)
        raw_ts = raw.get("timestamp") or raw.get("event_time") or raw.get("emitted_at")
        if isinstance(raw_ts, datetime):
            event_time = raw_ts if raw_ts.tzinfo else raw_ts.replace(tzinfo=UTC)
        elif isinstance(raw_ts, str):
            try:
                event_time = datetime.fromisoformat(raw_ts.replace("Z", "+00:00"))
            except Exception:
                event_time = now
        else:
            event_time = now

        # Clocks
        observed_time = observed_at or raw.get("observed_time") or event_time
        if isinstance(observed_time, str):
            try:
                observed_time = datetime.fromisoformat(observed_time.replace("Z", "+00:00"))
            except Exception:
                observed_time = event_time

        effective_time = effective_at or raw.get("effective_time") or event_time
        if isinstance(effective_time, str):
            try:
                effective_time = datetime.fromisoformat(effective_time.replace("Z", "+00:00"))
            except Exception:
                effective_time = event_time

        clocks = MultiClockTimestamps(
            event_time=event_time,
            observed_time=observed_time,
            ingested_time=ingested_time,
            processed_time=processed_time,
            effective_time=effective_time,
            valid_from=effective_time,
            valid_until=raw.get("valid_until"),
        )

        # Detect category
        prefix = event_type.split(".")[0].lower()
        category = cls.CATEGORY_MAPPINGS.get(prefix, "SYSTEM")

        # Untrusted / adversarial content inspection
        is_untrusted = False
        if source in ("untrusted_web", "external_api", "user_file", "third_party"):
            is_untrusted = True

        payload = raw.get("payload_json") or raw.get("payload") or {}
        if isinstance(payload, dict):
            # Check for instruction smuggling / spoofing markers
            payload_str = str(payload).lower()
            if any(term in payload_str for term in ("ignore previous", "system override", "authorization granted", "root access")):
                is_untrusted = True

        # Tracing links
        correlation_id = str(raw.get("correlation_id") or gen_temporal_id("corr"))
        causation_id = raw.get("causation_id")
        parent_event_id = raw.get("parent_event_id")
        actor_id = raw.get("actor_id") or raw.get("user_id")

        # Payload summary and diff
        payload_diff = raw.get("diff") or raw.get("payload_diff") or {}
        summary = str(raw.get("summary") or raw.get("description") or f"{event_type} from {source}")

        return TemporalEvent(
            temporal_event_id=gen_temporal_id("tevt"),
            canonical_event_id=canonical_id,
            event_type=event_type,
            event_version=str(raw.get("event_version") or "v1"),
            category=category,
            clocks=clocks,
            sequence_number=sequence_num or int(raw.get("sequence_number") or 0),
            monotonic_timestamp=monotonic_ts or float(raw.get("monotonic_timestamp") or 0.0),
            source_subsystem=source,
            source_entity_id=raw.get("entity_id") or raw.get("target_id") or raw.get("project_id"),
            actor_id=str(actor_id) if actor_id else None,
            correlation_id=correlation_id,
            causation_id=str(causation_id) if causation_id else None,
            parent_event_id=str(parent_event_id) if parent_event_id else None,
            payload_summary=summary[:256],
            payload_diff=payload_diff if isinstance(payload_diff, dict) else {},
            confidence=float(raw.get("confidence", 0.8 if is_untrusted else 1.0)),
            is_untrusted=is_untrusted,
            metadata=raw.get("metadata_json") or raw.get("metadata") or {},
        )
