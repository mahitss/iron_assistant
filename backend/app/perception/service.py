"""Master Perception & Environmental Awareness Service (Task 46)."""

from __future__ import annotations

from datetime import datetime, timezone
import logging
from typing import Any, Callable, Dict, List, Optional
import uuid

from app.perception.changes import ChangeDetector, ChangeEvent
from app.perception.context import PerceptionContext, RelevanceEngine
from app.perception.correlator import EventCorrelator
from app.perception.deduplication import EventDeduplicator
from app.perception.environment import EnvironmentBoundaryGuard
from app.perception.events import InvalidEventError, PerceptionEvent
from app.perception.freshness import FreshnessTracker
from app.perception.health import PerceptionHealthMetrics
from app.perception.normalizer import EventNormalizer
from app.perception.observations import Observation
from app.perception.ordering import EventOrderManager
from app.perception.privacy import PerceptionPrivacyGuard
from app.perception.provenance import ProvenanceTracker
from app.perception.reconciliation import EntityResolver, StateReconciler
from app.perception.redaction import SecretRedactor
from app.perception.situation import Anomaly, SituationalAwarenessManager
from app.perception.snapshots import EnvironmentSnapshot, SnapshotManager
from app.perception.sources import (
    PerceptionSource,
    SourceRegistry,
    SourceStatus,
    SourceType,
    SourceUnauthorizedError,
)

logger = logging.getLogger("kairo.perception.service")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class PerceptionService:
    """Canonical environmental awareness engine integrating multi-source telemetry into live awareness."""

    def __init__(self) -> None:
        self.sources = SourceRegistry()
        self.normalizer = EventNormalizer()
        self.deduplicator = EventDeduplicator()
        self.order_manager = EventOrderManager()
        self.freshness_tracker = FreshnessTracker()
        self.correlator = EventCorrelator()
        self.provenance_tracker = ProvenanceTracker()
        self.change_detector = ChangeDetector()
        self.snapshot_manager = SnapshotManager()
        self.reconciler = StateReconciler()
        self.entity_resolver = EntityResolver()
        self.situation_manager = SituationalAwarenessManager()
        self.metrics = PerceptionHealthMetrics()

        # In-memory store of recent observations: subject -> list of observations
        self._observations_by_subject: Dict[str, List[Observation]] = {}
        # Rate limit / backpressure queue bounds (Spec 151-153)
        self.max_queue_size = 1000
        self._pending_queue: List[Dict[str, Any]] = []

    def ingest_event(
        self,
        raw_event: Dict[str, Any],
        source_id: str,
        user_id: str = "default_user",
        project_id: str = "default_project",
        device_id: Optional[str] = None,
        environment: str = "DEVELOPMENT",
        has_explicit_user_consent: bool = False,
    ) -> Optional[tuple[Observation, Optional[ChangeEvent], Optional[Anomaly]]]:
        """Canonical ingestion pipeline:
        INGEST -> AUTH -> REDACT -> NORMALIZE -> DEDUP -> ORDER -> FRESHNESS -> OBSERVE -> PROVENANCE -> CORRELATE -> RECONCILE -> CHANGE -> ANOMALY -> SITUATION.
        """
        # 1. Validate Source Existence & Authorization (Spec 4, 178-181)
        source = self.sources.get_source(source_id)
        if not source:
            raise KeyError(f"Perception source '{source_id}' is not registered.")

        source.validate_authorization(user_id=user_id, project_id=project_id, device_id=device_id)

        # 2. Enforce Privacy Invariants & Anti-Surveillance (Spec 39-42, 197)
        PerceptionPrivacyGuard.validate_modal_capture_authorization(
            source=source,
            has_explicit_user_consent=has_explicit_user_consent,
        )

        # 3. Redact Secrets & Credentials (Spec 48, 52, 177)
        sanitized_raw, was_redacted = SecretRedactor.redact_payload(raw_event)

        # 4. Normalize Heterogeneous Event into PerceptionEvent (Spec 10-12)
        event = self.normalizer.normalize(sanitized_raw, source)
        event.scope.setdefault("environment", environment)
        event.scope.setdefault("project_id", project_id)
        event.scope.setdefault("user_id", user_id)

        # 5. Event Deduplication (Spec 16, 17)
        if self.deduplicator.is_duplicate(event):
            self.metrics.events_deduplicated += 1
            return None

        # 6. Sequence & Ordering (Spec 18, 19)
        in_order, order_status = self.order_manager.check_sequence(event)
        if not in_order:
            self.metrics.out_of_order_events += 1

        # 7. Clock Skew & Stale Update Protection (Spec 20-23)
        self.freshness_tracker.calculate_clock_skew(source.source_id, event.timestamp, event.received_at)
        if self.freshness_tracker.is_stale_update(event.subject, event.timestamp):
            self.metrics.stale_events_rejected += 1
            logger.info("Rejected stale event update for subject %s", event.subject)
            return None

        # 8. Construct Observation (Spec 6, 7)
        obs = Observation.from_event(event=event, source=source)
        self._observations_by_subject.setdefault(obs.subject, []).append(obs)

        # 9. Record Provenance (Spec 12)
        self.provenance_tracker.record_provenance(
            observation_id=obs.observation_id,
            source_id=source.source_id,
            source_type=source.type.value,
            adapter_name=obs.provenance.get("adapter", "Generic"),
            redaction_applied=was_redacted,
            signature_verified=event.is_authenticated,
        )

        # 10. Record & Correlate Event in Graph (Spec 24-28)
        self.correlator.record_event(event)

        # 11. State Reconciliation with Authoritative Sources (Spec 114-117)
        is_accepted, conflict = self.reconciler.reconcile_observation(obs, source)

        # 12. Change Detection & Significance Classification (Spec 79-86)
        change = self.change_detector.detect_change(
            observation=obs,
            environment=environment,
            is_security_sensitive=source.privacy_level.value in ["SENSITIVE", "RESTRICTED"],
        )
        if change:
            self.metrics.changes_detected += 1

        # 13. Anomaly Detection (Spec 89, 90)
        anomaly = None
        expected_status = sanitized_raw.get("expected_status")
        observed_status = obs.data.get("status") if isinstance(obs.data, dict) else None
        if expected_status and observed_status and expected_status != observed_status:
            anomaly = self.situation_manager.detect_anomaly(
                subject=obs.subject,
                expected=expected_status,
                observed=observed_status,
                confidence=obs.confidence,
            )
            if anomaly:
                self.metrics.anomalies_detected += 1

        # 14. Update Source Heartbeat & Liveness (Spec 160, 161)
        self.sources.record_heartbeat(source.source_id)

        # 15. Record Ingestion Metrics
        self.metrics.record_ingestion(obs.latency_ms)

        return obs, change, anomaly

    def get_live_situation(self, environment: str = "DEVELOPMENT", scope: Optional[Dict[str, Any]] = None) -> Any:
        """Synthesize situational awareness across all recent observations (Spec 100-106)."""
        all_obs: List[Observation] = []
        for obs_list in self._observations_by_subject.values():
            if obs_list:
                all_obs.append(obs_list[-1])

        # Identify missing/offline sources (Spec 34, 35)
        all_sources = self.sources.list_sources()
        unknown_sources = [s.name for s in all_sources if s.status in [SourceStatus.OFFLINE, SourceStatus.UNKNOWN, SourceStatus.DISABLED]]

        return self.situation_manager.synthesize_situation(
            scope=scope or {"environment": environment},
            observations=all_obs,
            changes=[],
            anomalies=[],
            unknown_sources=unknown_sources,
        )

    def get_relevant_observations(self, context: PerceptionContext, max_items: int = 10) -> List[Observation]:
        """Rank and filter observations for bounded model context (Spec 107-110)."""
        candidates: List[Observation] = []
        for obs_list in self._observations_by_subject.values():
            if obs_list:
                candidates.append(obs_list[-1])
        return RelevanceEngine.rank_observations(candidates, context=context, max_items=max_items)

    def replay_events(self, events: List[Dict[str, Any]], source: PerceptionSource) -> List[Observation]:
        """Enforce Spec 166, 167: Deterministic replay for debugging WITHOUT executing external side effects."""
        replayed: List[Observation] = []
        for raw in events:
            event = self.normalizer.normalize(raw, source)
            obs = Observation.from_event(event=event, source=source)
            replayed.append(obs)
        logger.info("Deterministically replayed %d events without side effects", len(replayed))
        return replayed
