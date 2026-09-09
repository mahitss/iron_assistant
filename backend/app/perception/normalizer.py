"""Event Normalization Pipeline, Adapter Dispatch, and Schema Ingestion (Task 46)."""

from __future__ import annotations

from datetime import datetime, timezone
import logging
from typing import Any, Dict, Optional, Type

from app.perception.adapters import (
    AgentAdapter,
    AutomationAdapter,
    BaseSourceAdapter,
    BrowserAdapter,
    CalendarAdapter,
    DeploymentAdapter,
    DeviceAdapter,
    FileSystemAdapter,
    GitAdapter,
    GitHubAdapter,
    NotificationAdapter,
    ServiceHealthAdapter,
    TaskEngineAdapter,
    VisionAdapter,
    VoiceAdapter,
)
from app.perception.events import InvalidEventError, PerceptionEvent
from app.perception.sources import PerceptionSource, SourceType

logger = logging.getLogger("kairo.perception.normalizer")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class EventNormalizer:
    """Dispatches raw environmental telemetry to appropriate adapters and enforces common schema (Spec 10-12)."""

    def __init__(self) -> None:
        self._adapters: Dict[SourceType, BaseSourceAdapter] = {
            SourceType.DEVICE: DeviceAdapter(),
            SourceType.DESKTOP: DeviceAdapter(),
            SourceType.APPLICATION: DeviceAdapter(),
            SourceType.BROWSER: BrowserAdapter(),
            SourceType.FILE_SYSTEM: FileSystemAdapter(),
            SourceType.GIT: GitAdapter(),
            SourceType.GITHUB: GitHubAdapter(),
            SourceType.DEPLOYMENT: DeploymentAdapter(),
            SourceType.SERVICE: ServiceHealthAdapter(),
            SourceType.NOTIFICATION: NotificationAdapter(),
            SourceType.VOICE: VoiceAdapter(),
            SourceType.VISION: VisionAdapter(),
            SourceType.TASK_ENGINE: TaskEngineAdapter(),
            SourceType.AGENT: AgentAdapter(),
            SourceType.AUTOMATION: AutomationAdapter(),
            SourceType.CALENDAR: CalendarAdapter(),
        }

    def register_adapter(self, source_type: SourceType, adapter: BaseSourceAdapter) -> None:
        self._adapters[source_type] = adapter

    def normalize(self, raw_event: Dict[str, Any], source: PerceptionSource) -> PerceptionEvent:
        """Normalize heterogeneous event into standard PerceptionEvent contract (Spec 10, 12)."""
        adapter = self._adapters.get(source.type)
        if not adapter:
            # Generic fallback adapter
            event = PerceptionEvent(
                event_id=raw_event.get("event_id", f"gen_{source.source_id[:6]}_{int(utc_now().timestamp())}"),
                event_type=raw_event.get("event_type", "UPDATED"),
                source_id=source.source_id,
                subject=raw_event.get("subject", f"{source.type.value}:{source.source_id}"),
                timestamp=raw_event.get("timestamp", utc_now()),
                sequence=raw_event.get("sequence", 0),
                payload=raw_event.get("payload", raw_event),
                scope=raw_event.get("scope", {}),
                correlation_id=raw_event.get("correlation_id"),
                provenance={"adapter": "GenericFallback", "source_type": source.type.value},
            )
        else:
            event = adapter.adapt(raw_event, source)

        # Enforce validation (Spec 13, 150)
        event.validate()
        return event
