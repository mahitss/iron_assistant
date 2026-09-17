"""Signal normalization pipeline and domain adapters for Task 99.

Converts heterogeneous existing events, telemetry, and subsystem findings into canonical SignalRecord instances.
Enforces trust classification, prompt injection sanitization, and strict provenance.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import UTC, datetime
import logging
from typing import Any, Dict, List, Optional

from app.situational_awareness.domain import (
    SignalRecord,
    SituationSeverity,
    SourceTrustLevel,
    generate_uuid,
    utc_now,
)
from app.situational_awareness.privacy import situational_privacy_manager
from app.situational_awareness.safety import sanitize_situation_directive
from app.situational_awareness.schemas import (
    EventIngestRequest,
    NormalizedEvent,
    SignalIngestRequest,
)

logger = logging.getLogger("kairo.situational_awareness.normalization")

_SOURCE_TRUST_MAP: dict[str, SourceTrustLevel] = {
    "system": SourceTrustLevel.TRUSTED_SYSTEM,
    "telemetry": SourceTrustLevel.TRUSTED_SYSTEM,
    "cloudwatch": SourceTrustLevel.TRUSTED_SYSTEM,
    "prometheus": SourceTrustLevel.TRUSTED_SYSTEM,
    "k8s": SourceTrustLevel.TRUSTED_SYSTEM,
    "world_state": SourceTrustLevel.TRUSTED_SYSTEM,
    "action_transaction": SourceTrustLevel.TRUSTED_SYSTEM,
    "reliability_intelligence": SourceTrustLevel.TRUSTED_SYSTEM,
    "risk_engine": SourceTrustLevel.TRUSTED_SYSTEM,
    "github_webhook": SourceTrustLevel.VERIFIED_EXTERNAL,
    "datadog": SourceTrustLevel.VERIFIED_EXTERNAL,
    "user_ui": SourceTrustLevel.USER_REPORTED,
    "chat_prompt": SourceTrustLevel.USER_AUTHORED,
    "model_agent": SourceTrustLevel.MODEL_GENERATED,
    "swarm_agent": SourceTrustLevel.AGENT_DERIVED,
    "simulator": SourceTrustLevel.SIMULATED,
    "random_external": SourceTrustLevel.UNVERIFIED_EXTERNAL,
}

_TRUST_CONFIDENCE_MAP: dict[SourceTrustLevel, float] = {
    SourceTrustLevel.TRUSTED_SYSTEM: 1.0,
    SourceTrustLevel.TRUSTED_INTERNAL: 1.0,
    SourceTrustLevel.VERIFIED_EXTERNAL: 0.95,
    SourceTrustLevel.USER_REPORTED: 0.85,
    SourceTrustLevel.USER_AUTHORED: 0.85,
    SourceTrustLevel.MODEL_GENERATED: 0.80,
    SourceTrustLevel.MODEL_DERIVED: 0.80,
    SourceTrustLevel.AGENT_DERIVED: 0.80,
    SourceTrustLevel.SIMULATED: 0.85,
    SourceTrustLevel.UNVERIFIED_EXTERNAL: 0.50,
    SourceTrustLevel.EXTERNAL_UNTRUSTED: 0.50,
    SourceTrustLevel.TOOL_UNTRUSTED: 0.50,
    SourceTrustLevel.WEB_UNTRUSTED: 0.40,
    SourceTrustLevel.CODE_UNTRUSTED: 0.45,
    SourceTrustLevel.SCREEN_UNTRUSTED: 0.45,
}


# =====================================================================
# ADAPTER INTERFACES (Section 4)
# =====================================================================

class SignalAdapter(ABC):
    """Abstract adapter transforming raw subsystem events into canonical SignalRecords."""

    @abstractmethod
    def can_adapt(self, raw_data: Any) -> bool:
        pass

    @abstractmethod
    def adapt(self, raw_data: Any) -> SignalRecord:
        pass


class WorldStateDriftSignalAdapter(SignalAdapter):
    """Adapts Task 98 World-State drift records and conflict events."""

    def can_adapt(self, raw_data: Any) -> bool:
        if isinstance(raw_data, dict):
            return "drift_type" in raw_data or raw_data.get("event_type") in ("state.drift_detected", "state.conflict_detected")
        return hasattr(raw_data, "drift_type") or hasattr(raw_data, "drift_id")

    def adapt(self, raw_data: Any) -> SignalRecord:
        if isinstance(raw_data, dict):
            drift_id = raw_data.get("drift_id", generate_uuid("drift"))
            entity_id = raw_data.get("entity_id", "unknown_entity")
            drift_type = raw_data.get("drift_type", "STATE_DRIFT")
            severity = raw_data.get("severity", "MEDIUM")
            expected = raw_data.get("expected_value")
            actual = raw_data.get("actual_value", raw_data.get("observed_value"))
            classification = raw_data.get("classification", "ACTIONABLE_DRIFT")
            causal_status = raw_data.get("causal_status", "UNKNOWN")
            scope = raw_data.get("scope", "SYSTEM")
            ts = raw_data.get("detected_at") or utc_now()
        else:
            drift_id = getattr(raw_data, "drift_id", generate_uuid("drift"))
            entity_id = getattr(raw_data, "entity_id", "unknown_entity")
            drift_type = getattr(raw_data, "drift_type", "STATE_DRIFT")
            severity = getattr(raw_data, "severity", "MEDIUM")
            expected = getattr(raw_data, "expected_value", None)
            actual = getattr(raw_data, "actual_value", getattr(raw_data, "observed_value", None))
            classification = getattr(raw_data, "classification", "ACTIONABLE_DRIFT")
            causal_status = getattr(raw_data, "causal_status", "UNKNOWN")
            scope = getattr(raw_data, "scope", "SYSTEM")
            ts = getattr(raw_data, "detected_at", utc_now())

        if hasattr(drift_type, "value"):
            drift_type = drift_type.value
        if hasattr(severity, "value"):
            severity = severity.value
        if hasattr(scope, "value"):
            scope = scope.value

        return SignalRecord(
            signal_id=f"sig_{drift_id}",
            source_type="WORLD_STATE_DRIFT",
            source_id="reconciliation_engine",
            signal_type="WORLD_STATE_DRIFT",
            subject=entity_id,
            scope=str(scope),
            observed_at=ts,
            confidence=1.0,
            trust_level=SourceTrustLevel.TRUSTED_INTERNAL,
            sensitivity="INTERNAL",
            correlation_keys=[entity_id, f"drift:{drift_type.lower()}"],
            world_state_refs=[drift_id, entity_id],
            payload={
                "drift_id": drift_id,
                "entity_id": entity_id,
                "drift_type": str(drift_type),
                "severity": str(severity),
                "expected_value": expected,
                "actual_value": actual,
                "classification": str(classification),
                "causal_status": str(causal_status),
            },
            provenance={"generator": "WorldStateReconciliationEngine", "drift_id": drift_id},
        )


class ExecutionSignalAdapter(SignalAdapter):
    """Adapts Task 95 ActionTransaction lifecycle and postcondition outcomes."""

    def can_adapt(self, raw_data: Any) -> bool:
        if isinstance(raw_data, dict):
            return "transaction_id" in raw_data or raw_data.get("event_type", "").startswith("action.")
        return hasattr(raw_data, "transaction_id")

    def adapt(self, raw_data: Any) -> SignalRecord:
        tx_id = raw_data.get("transaction_id") if isinstance(raw_data, dict) else getattr(raw_data, "transaction_id", "")
        status = raw_data.get("status") if isinstance(raw_data, dict) else getattr(raw_data, "status", "UNKNOWN")
        target_entity = raw_data.get("target_entity_id") if isinstance(raw_data, dict) else getattr(raw_data, "target_entity_id", "")
        action_name = raw_data.get("action_name") if isinstance(raw_data, dict) else getattr(raw_data, "action_name", "action")

        sig_type = "ACTION_FAILURE" if str(status) in ("FAILED", "BLOCKED") else "ACTION_COMPLETED"
        return SignalRecord(
            signal_id=f"sig_tx_{tx_id}",
            source_type="ACTION_TRANSACTION",
            source_id="execution_service",
            signal_type=sig_type,
            subject=target_entity or action_name,
            scope="SYSTEM",
            confidence=1.0,
            trust_level=SourceTrustLevel.TRUSTED_INTERNAL,
            correlation_keys=[target_entity, tx_id] if target_entity else [tx_id],
            decision_refs=[tx_id],
            payload={"transaction_id": tx_id, "status": str(status), "target_entity": target_entity, "action": action_name},
            provenance={"generator": "ExecutionService", "transaction_id": tx_id},
        )


class RiskSignalAdapter(SignalAdapter):
    """Adapts Risk Engine findings and cascade predictions."""

    def can_adapt(self, raw_data: Any) -> bool:
        if isinstance(raw_data, dict):
            return "risk_score" in raw_data or raw_data.get("event_type", "").startswith("risk.")
        return hasattr(raw_data, "risk_score")

    def adapt(self, raw_data: Any) -> SignalRecord:
        score = raw_data.get("risk_score", 0.5) if isinstance(raw_data, dict) else getattr(raw_data, "risk_score", 0.5)
        entity = raw_data.get("entity_id", "system") if isinstance(raw_data, dict) else getattr(raw_data, "entity_id", "system")
        category = raw_data.get("category", "OPERATIONAL") if isinstance(raw_data, dict) else getattr(raw_data, "category", "OPERATIONAL")
        return SignalRecord(
            source_type="RISK_ENGINE",
            source_id="risk_evaluator",
            signal_type="RISK_INCREASE" if score > 0.6 else "RISK_EVALUATION",
            subject=entity,
            scope="SYSTEM",
            confidence=0.9,
            trust_level=SourceTrustLevel.TRUSTED_INTERNAL,
            correlation_keys=[entity, f"risk:{category.lower()}"],
            payload={"risk_score": score, "entity_id": entity, "category": category},
            provenance={"generator": "RiskEngine"},
        )


class ForecastSignalAdapter(SignalAdapter):
    """Adapts Foresight & Forecasting engine predicted threshold crossings."""

    def can_adapt(self, raw_data: Any) -> bool:
        if isinstance(raw_data, dict):
            return "forecast_id" in raw_data or "predicted_threshold" in raw_data
        return hasattr(raw_data, "forecast_id")

    def adapt(self, raw_data: Any) -> SignalRecord:
        fid = raw_data.get("forecast_id", "") if isinstance(raw_data, dict) else getattr(raw_data, "forecast_id", "")
        metric = raw_data.get("metric_name", "capacity") if isinstance(raw_data, dict) else getattr(raw_data, "metric_name", "capacity")
        pred_val = raw_data.get("predicted_value") if isinstance(raw_data, dict) else getattr(raw_data, "predicted_value", None)
        entity = raw_data.get("entity_id", "service") if isinstance(raw_data, dict) else getattr(raw_data, "entity_id", "service")
        target_time = raw_data.get("target_time") if isinstance(raw_data, dict) else getattr(raw_data, "target_time", None)

        return SignalRecord(
            signal_id=f"sig_fc_{fid}" if fid else generate_uuid("sig"),
            source_type="FORESIGHT",
            source_id="forecasting_engine",
            signal_type="FORECAST_THRESHOLD",
            subject=entity,
            scope="SYSTEM",
            effective_at=target_time,
            confidence=0.85,
            trust_level=SourceTrustLevel.SIMULATED,
            correlation_keys=[entity, f"metric:{metric}"],
            payload={"forecast_id": fid, "metric": metric, "predicted_value": pred_val, "target_time": str(target_time)},
            provenance={"generator": "ForecastingEngine", "forecast_id": fid},
        )


class ReliabilitySignalAdapter(SignalAdapter):
    """Adapts Task 90 Reliability Intelligence degradation and crash loop findings."""

    def can_adapt(self, raw_data: Any) -> bool:
        if isinstance(raw_data, dict):
            return "reliability_score" in raw_data or "crash_loops" in raw_data or raw_data.get("event_type", "").startswith("reliability.")
        return hasattr(raw_data, "reliability_score")

    def adapt(self, raw_data: Any) -> SignalRecord:
        entity = raw_data.get("entity_id", "node") if isinstance(raw_data, dict) else getattr(raw_data, "entity_id", "node")
        deg = raw_data.get("degradation_pct", 0.0) if isinstance(raw_data, dict) else getattr(raw_data, "degradation_pct", 0.0)
        return SignalRecord(
            source_type="RELIABILITY_INTELLIGENCE",
            source_id="reliability_service",
            signal_type="RELIABILITY_DEGRADATION",
            subject=entity,
            scope="SYSTEM",
            confidence=0.95,
            trust_level=SourceTrustLevel.TRUSTED_INTERNAL,
            correlation_keys=[entity, "reliability:degraded"],
            payload={"entity_id": entity, "degradation_pct": deg},
            provenance={"generator": "ReliabilityIntelligence"},
        )


class CapabilitySignalAdapter(SignalAdapter):
    """Adapts Capability lifecycle deprecation, failure, or version mismatch findings."""

    def can_adapt(self, raw_data: Any) -> bool:
        if isinstance(raw_data, dict):
            return "capability_id" in raw_data or "capability_version" in raw_data
        return hasattr(raw_data, "capability_id")

    def adapt(self, raw_data: Any) -> SignalRecord:
        cid = raw_data.get("capability_id", "cap") if isinstance(raw_data, dict) else getattr(raw_data, "capability_id", "cap")
        ver = raw_data.get("version", "v1") if isinstance(raw_data, dict) else getattr(raw_data, "version", "v1")
        status = raw_data.get("status", "CHANGED") if isinstance(raw_data, dict) else getattr(raw_data, "status", "CHANGED")
        return SignalRecord(
            source_type="CAPABILITY_LIFECYCLE",
            source_id="capability_service",
            signal_type="CAPABILITY_CHANGED",
            subject=cid,
            scope="SYSTEM",
            confidence=1.0,
            trust_level=SourceTrustLevel.TRUSTED_INTERNAL,
            correlation_keys=[cid, f"cap_ver:{ver}"],
            payload={"capability_id": cid, "version": ver, "status": status},
            provenance={"generator": "CapabilityLifecycle"},
        )


class SwarmSignalAdapter(SignalAdapter):
    """Adapts Task 96 Swarm agent stall, task failures, or deadlock reports."""

    def can_adapt(self, raw_data: Any) -> bool:
        if isinstance(raw_data, dict):
            return "agent_id" in raw_data and ("stall_detected" in raw_data or raw_data.get("event_type", "").startswith("swarm."))
        return hasattr(raw_data, "agent_id") and hasattr(raw_data, "stall_detected")

    def adapt(self, raw_data: Any) -> SignalRecord:
        aid = raw_data.get("agent_id", "agent") if isinstance(raw_data, dict) else getattr(raw_data, "agent_id", "agent")
        reason = raw_data.get("reason", "Agent stalled") if isinstance(raw_data, dict) else getattr(raw_data, "reason", "Agent stalled")
        return SignalRecord(
            source_type="SWARM_ORCHESTRATION",
            source_id="swarm_supervisor",
            signal_type="AGENT_STALLED",
            subject=aid,
            scope="SYSTEM",
            confidence=0.9,
            trust_level=SourceTrustLevel.AGENT_DERIVED,
            correlation_keys=[aid, "swarm:stalled"],
            payload={"agent_id": aid, "reason": reason},
            provenance={"generator": "SwarmSupervisor"},
        )


# =====================================================================
# MAIN NORMALIZER PIPELINE
# =====================================================================

class SignalNormalizer:
    """Master signal normalization pipeline coordinating all registered domain adapters."""

    def __init__(self) -> None:
        self.adapters: list[SignalAdapter] = [
            WorldStateDriftSignalAdapter(),
            ExecutionSignalAdapter(),
            RiskSignalAdapter(),
            ForecastSignalAdapter(),
            ReliabilitySignalAdapter(),
            CapabilitySignalAdapter(),
            SwarmSignalAdapter(),
        ]

    def register_adapter(self, adapter: SignalAdapter) -> None:
        self.adapters.insert(0, adapter)

    def normalize(self, raw_input: Any) -> SignalRecord:
        """Normalizes any heterogeneous input into a canonical, poison-resistant SignalRecord."""
        # 1. Try registered adapters first
        for adapter in self.adapters:
            if adapter.can_adapt(raw_input):
                return adapter.adapt(raw_input)

        # 2. Handle SignalIngestRequest
        if isinstance(raw_input, SignalIngestRequest):
            clean_sub = sanitize_situation_directive(raw_input.subject)
            trust = raw_input.trust_level or _SOURCE_TRUST_MAP.get(
                raw_input.source_type.lower(), SourceTrustLevel.TRUSTED_INTERNAL
            )
            conf = raw_input.confidence or _TRUST_CONFIDENCE_MAP.get(trust, 0.8)
            clean_payload = situational_privacy_manager.sanitize_payload(raw_input.payload)

            return SignalRecord(
                source_type=raw_input.source_type,
                source_id=raw_input.source_id,
                source_version=raw_input.source_version,
                signal_type=raw_input.signal_type,
                subject=clean_sub,
                scope=raw_input.scope,
                payload=clean_payload,
                confidence=conf,
                trust_level=trust,
                severity=getattr(raw_input, "severity", SituationSeverity.INFO),
                sensitivity=raw_input.sensitivity,
                correlation_keys=raw_input.correlation_keys or ([clean_sub] if clean_sub else []),
                causal_refs=raw_input.causal_refs,
                world_state_refs=raw_input.world_state_refs,
                decision_refs=raw_input.decision_refs,
                trace_id=raw_input.trace_id,
                correlation_id=raw_input.correlation_id,
                event_id=raw_input.event_id,
                observed_at=raw_input.observed_at or utc_now(),
                provenance=raw_input.provenance or {"source": raw_input.source_type},
            )

        # 3. Handle backward-compatible EventIngestRequest
        if isinstance(raw_input, EventIngestRequest):
            clean_sub = sanitize_situation_directive(raw_input.subject)
            trust = raw_input.source_trust or _SOURCE_TRUST_MAP.get(
                raw_input.source.lower(), SourceTrustLevel.TRUSTED_SYSTEM
            )
            conf = _TRUST_CONFIDENCE_MAP.get(trust, 1.0)
            clean_payload = situational_privacy_manager.sanitize_payload(raw_input.payload)
            obs_at = raw_input.occurred_at or utc_now()
            prov = {
                "original_source": raw_input.source,
                "is_sanitized": True,
                "source": raw_input.source,
            }

            return NormalizedEvent(
                event_type=raw_input.event_type,
                source=raw_input.source,
                original_source=raw_input.source,
                is_sanitized=True,
                subject=clean_sub,
                environment=raw_input.environment,
                resource=raw_input.resource,
                actor=raw_input.actor,
                payload=clean_payload,
                severity=raw_input.severity,
                source_trust=trust,
                confidence=conf,
                occurred_at=obs_at,
                received_at=utc_now(),
                provenance=prov,
            )

        # 4. Handle NormalizedEvent directly
        if isinstance(raw_input, NormalizedEvent):
            return raw_input

        # 5. Fallback for raw dictionaries
        if isinstance(raw_input, dict):
            src_type = raw_input.get("source_type", raw_input.get("source", "TELEMETRY"))
            trust = _SOURCE_TRUST_MAP.get(str(src_type).lower(), SourceTrustLevel.TRUSTED_INTERNAL)
            subj = sanitize_situation_directive(str(raw_input.get("subject", raw_input.get("entity_id", "system"))))
            sig_type = raw_input.get("signal_type", raw_input.get("event_type", "OBSERVATION"))
            clean_payload = situational_privacy_manager.sanitize_payload(raw_input.get("payload", {}))

            return SignalRecord(
                signal_id=raw_input.get("signal_id", raw_input.get("event_id", generate_uuid("sig"))),
                source_type=str(src_type).upper(),
                source_id=str(raw_input.get("source_id", "generic")),
                signal_type=str(sig_type).upper(),
                subject=subj,
                scope=str(raw_input.get("scope", "SYSTEM")),
                payload=clean_payload,
                confidence=float(raw_input.get("confidence", 1.0)),
                trust_level=trust,
                correlation_keys=raw_input.get("correlation_keys", [subj] if subj else []),
                trace_id=raw_input.get("trace_id"),
                correlation_id=raw_input.get("correlation_id"),
                observed_at=raw_input.get("observed_at", utc_now()),
                provenance=raw_input.get("provenance", {"source": src_type, "original_source": src_type, "is_sanitized": True}),
            )

        # 6. Direct SignalRecord passthrough
        if isinstance(raw_input, SignalRecord):
            return raw_input

    def normalize_signal(self, raw_input: Any) -> SignalRecord:
        """Normalizes input directly returning a SignalRecord."""
        res = self.normalize(raw_input)
        if isinstance(res, NormalizedEvent):
            return res.to_signal()
        return res

    def normalize_legacy_event(self, raw_input: Any) -> SignalRecord:
        """Alias for normalize to handle legacy EventIngestRequest returning a SignalRecord."""
        return self.normalize_signal(raw_input)


# Global normalizer instance & legacy aliases
signal_normalizer = SignalNormalizer()
SignalNormalizationPipeline = SignalNormalizer
EventNormalizer = SignalNormalizer
event_normalizer = signal_normalizer
