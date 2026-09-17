"""Multi-dimensional signal correlation engine and temporal reasoning for Task 99.

Evaluates correlation across 7 dimensions:
1. Temporal: sliding windows, burst detection, escalating frequency, sequence patterns
2. Entity: same entity, related entity
3. Scope: same project, workflow, goal, capability, resource
4. Causal: causal links and references
5. Graph: multi-hop knowledge graph relationships
6. Operational: trace ID, correlation ID, action transaction ID
7. Semantic: compatible signal types and structured tags

Enforces:
- CORRELATION != CAUSATION
- Deterministic evaluation first
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
import hashlib
import json
import logging
from typing import Any, Dict, List, Optional, Set

from app.situational_awareness.domain import SignalRecord

logger = logging.getLogger("kairo.situational_awareness.correlation")


class SignalCorrelator:
    """Multi-dimensional correlation engine evaluating affinity between operational signals."""

    def __init__(
        self,
        default_window_seconds: float = 300.0,
        temporal_window_seconds: Optional[float] = None,
        burst_threshold_count: int = 5,
        burst_window_seconds: float = 30.0,
    ) -> None:
        self.default_window = temporal_window_seconds if temporal_window_seconds is not None else default_window_seconds
        self.temporal_window_seconds = self.default_window
        self.burst_threshold_count = burst_threshold_count
        self.burst_window_seconds = burst_window_seconds
        self._entity_signal_history: dict[str, list[datetime]] = {}
        self._seen_signal_fps: dict[str, tuple[datetime, str]] = {}

    def check_and_deduplicate(self, signal: Any, recent_signals: Optional[list[Any]] = None) -> tuple[bool, str | None]:
        """Check if an incoming signal or event is a duplicate within a sliding time window."""
        src = getattr(signal, "source_id", getattr(signal, "source", ""))
        sig_type = getattr(signal, "signal_type", getattr(signal, "event_type", ""))
        subj = getattr(signal, "subject", "")
        scope = getattr(signal, "scope", getattr(signal, "environment", ""))
        sig_id = getattr(signal, "signal_id", getattr(signal, "event_id", ""))
        obs_at = getattr(signal, "observed_at", getattr(signal, "occurred_at", None)) or datetime.now(timezone.utc)
        epoch = obs_at.timestamp() if hasattr(obs_at, "timestamp") else 0.0
        bucket = int(epoch / 120.0)
        parts = {
            "source": str(src or "").lower(),
            "type": str(sig_type or "").lower(),
            "subject": str(subj or "").lower(),
            "scope": str(scope or "").lower(),
            "bucket": bucket,
        }
        fp = hashlib.sha256(json.dumps(parts, sort_keys=True).encode("utf-8")).hexdigest()
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(seconds=600)
        self._seen_signal_fps = {k: v for k, v in self._seen_signal_fps.items() if v[0] >= cutoff}

        if fp in self._seen_signal_fps:
            first_seen, orig_id = self._seen_signal_fps[fp]
            return True, orig_id
        self._seen_signal_fps[fp] = (now, sig_id)
        return False, None

    def calculate_correlation_score(
        self,
        signal_a: SignalRecord,
        signal_b: SignalRecord,
        dependency_map: Optional[dict[str, list[str]]] = None,
        graph_engine: Optional[Any] = None,
    ) -> float:
        """Calculates and returns composite correlation similarity score."""
        res = self.correlate(signal_a, signal_b, dependency_map, graph_engine)
        return float(res.get("correlation_score", 0.0))

    def correlate_signals(
        self,
        signal_a: SignalRecord,
        signal_b: SignalRecord,
        dependency_map: Optional[dict[str, list[str]]] = None,
        graph_engine: Optional[Any] = None,
    ) -> tuple[float, list[str]]:
        """Evaluates correlation and returns (score, reasons) tuple for engine integration."""
        res = self.correlate(signal_a, signal_b, dependency_map, graph_engine)
        return float(res.get("correlation_score", 0.0)), list(res.get("reasons", []))

    def correlate_events(
        self,
        event_a: Any,
        event_b: Any,
        dependency_map: Optional[dict[str, list[str]]] = None,
    ) -> dict[str, Any]:
        """Legacy event correlation supporting NormalizedEvent and Task 60 backward compatibility."""
        env_a = getattr(event_a, "environment", None)
        env_b = getattr(event_b, "environment", None)
        if env_a and env_b and env_a.lower() != env_b.lower():
            return {
                "is_correlated": False,
                "correlation_score": 0.0,
                "reasons": ["Environment mismatch prevents correlation"],
                "temporal_relationship": "INDEPENDENT",
            }

        t_a = getattr(event_a, "occurred_at", None) or getattr(event_a, "observed_at", None) or getattr(event_a, "received_at", None)
        t_b = getattr(event_b, "occurred_at", None) or getattr(event_b, "observed_at", None) or getattr(event_b, "received_at", None)

        time_diff = abs((t_a - t_b).total_seconds()) if (t_a and t_b) else 0.0
        is_temporally_close = time_diff <= self.default_window

        if t_a and t_b:
            if t_a < t_b:
                temporal_rel = "BEFORE"
            elif t_a > t_b:
                temporal_rel = "AFTER"
            else:
                temporal_rel = "SIMULTANEOUS"
        else:
            temporal_rel = "SIMULTANEOUS"

        res_a = (getattr(event_a, "resource", "") or getattr(event_a, "subject", "") or "").lower()
        res_b = (getattr(event_b, "resource", "") or getattr(event_b, "subject", "") or "").lower()

        same_resource = bool(res_a and res_b and res_a == res_b)

        dep_map = dependency_map or {}
        dep_match = False
        deps_for_b = [d.lower() for d in dep_map.get(res_b, [])] + [d.lower() for d in dep_map.get(getattr(event_b, "resource", ""), [])]
        deps_for_a = [d.lower() for d in dep_map.get(res_a, [])] + [d.lower() for d in dep_map.get(getattr(event_a, "resource", ""), [])]
        if res_a in deps_for_b or res_b in deps_for_a:
            dep_match = True

        reasons: list[str] = []
        if is_temporally_close:
            reasons.append(f"Occurred within temporal window: {time_diff:.1f}s")
        if same_resource:
            reasons.append(f"Events share identical resource: {res_a}")
        if dep_match:
            reasons.append(f"Linked via dependency graph topology: {res_a} <-> {res_b}")

        if same_resource and is_temporally_close:
            score = 0.85
            is_corr = True
        elif dep_match and is_temporally_close:
            score = 0.75
            is_corr = True
        elif is_temporally_close:
            score = 0.35
            is_corr = False
        else:
            score = 0.0
            is_corr = False

        return {
            "is_correlated": is_corr,
            "correlation_score": score,
            "reasons": reasons,
            "temporal_relationship": temporal_rel,
            "time_difference_seconds": round(time_diff, 1),
        }

    def correlate(
        self,
        signal_a: SignalRecord,
        signal_b: SignalRecord,
        dependency_map: Optional[dict[str, list[str]]] = None,
        graph_engine: Optional[Any] = None,
    ) -> dict[str, Any]:
        """Evaluates multi-dimensional correlation score between two canonical signals."""
        reasons: list[str] = []

        # 0. Operational Trace / Correlation ID match (Strongest operational link)
        operational_match = False
        if signal_a.trace_id and signal_b.trace_id and signal_a.trace_id == signal_b.trace_id:
            operational_match = True
            reasons.append(f"Share identical trace_id '{signal_a.trace_id}'")
        elif signal_a.correlation_id and signal_b.correlation_id and signal_a.correlation_id == signal_b.correlation_id:
            operational_match = True
            reasons.append(f"Share identical correlation_id '{signal_a.correlation_id}'")

        # 1. Temporal Dimension
        time_diff = abs((signal_a.observed_at - signal_b.observed_at).total_seconds())
        is_temporally_close = time_diff <= self.default_window
        temporal_score = max(0.0, 1.0 - (time_diff / self.default_window)) if is_temporally_close else 0.0
        if is_temporally_close:
            reasons.append(f"Temporal proximity within {time_diff:.1f}s window")

        # 2. Entity Dimension
        same_subject = bool(signal_a.subject and signal_b.subject and signal_a.subject.lower() == signal_b.subject.lower())
        same_entity = bool(signal_a.entity and signal_b.entity and signal_a.entity.lower() == signal_b.entity.lower())
        shared_keys = set(signal_a.correlation_keys) & set(signal_b.correlation_keys)
        entity_score = 1.0 if (same_subject or same_entity) else (0.8 if shared_keys else 0.0)
        if same_subject:
            reasons.append(f"Direct subject match '{signal_a.subject}'")
        elif same_entity:
            reasons.append(f"Direct entity match '{signal_a.entity}'")
        elif shared_keys:
            reasons.append(f"Shared correlation keys: {list(shared_keys)}")

        # 3. Scope Dimension
        same_scope = bool(signal_a.scope and signal_b.scope and signal_a.scope.upper() == signal_b.scope.upper())
        scope_score = 1.0 if same_scope else 0.3
        if same_scope:
            reasons.append(f"Identical operational scope '{signal_a.scope}'")

        # 4. Causal Dimension
        causal_match = False
        if any(ref in signal_b.causal_refs for ref in signal_a.causal_refs):
            causal_match = True
            reasons.append("Linked via explicit causal model references")
        causal_score = 1.0 if causal_match else 0.0

        # 5. Graph / Dependency Dimension
        dependency_match = False
        deps = dependency_map or {}
        sub_a = signal_a.subject.lower()
        sub_b = signal_b.subject.lower()
        if sub_a in deps.get(sub_b, []) or sub_b in deps.get(sub_a, []):
            dependency_match = True
            reasons.append(f"Dependency relation between '{signal_a.subject}' and '{signal_b.subject}'")
        elif graph_engine is not None:
            try:
                path = graph_engine.find_shortest_path(signal_a.subject, signal_b.subject, max_depth=3)
                if path and len(path) > 1:
                    dependency_match = True
                    reasons.append(f"Connected in Knowledge Graph across {len(path)-1} hops")
            except Exception:
                pass
        graph_score = 1.0 if dependency_match else 0.0

        # 6. Semantic Dimension (Compatible signal types that co-occur in incidents)
        semantic_pairs = {
            ("WORLD_STATE_DRIFT", "RISK_INCREASE"),
            ("WORLD_STATE_DRIFT", "RELIABILITY_DEGRADATION"),
            ("ACTION_FAILURE", "RELIABILITY_DEGRADATION"),
            ("RELIABILITY_DEGRADATION", "FORECAST_THRESHOLD"),
            ("CAPABILITY_CHANGED", "ACTION_FAILURE"),
            ("AGENT_STALLED", "ACTION_FAILURE"),
        }
        sig_pair = (signal_a.signal_type, signal_b.signal_type)
        sig_pair_rev = (signal_b.signal_type, signal_a.signal_type)
        semantic_score = 0.8 if (sig_pair in semantic_pairs or sig_pair_rev in semantic_pairs) else 0.2

        # Weighted Composite Score
        if operational_match and is_temporally_close:
            composite = 0.95
        else:
            composite = (
                (temporal_score * 0.25)
                + (entity_score * 0.30)
                + (graph_score * 0.15)
                + (causal_score * 0.10)
                + (scope_score * 0.10)
                + (semantic_score * 0.10)
            )

        if (same_subject or same_entity or shared_keys) and is_temporally_close:
            composite = max(composite, 0.75)

        is_correlated = bool(
            operational_match
            or (same_subject and is_temporally_close)
            or (same_entity and is_temporally_close)
            or (bool(shared_keys) and is_temporally_close)
            or (dependency_match and is_temporally_close)
            or composite >= 0.55
        )

        return {
            "is_correlated": is_correlated,
            "correlation_score": round(min(1.0, composite), 3),
            "time_difference_seconds": round(time_diff, 1),
            "reasons": reasons,
            "operational_match": operational_match,
            "entity_match": same_subject,
            "dependency_match": dependency_match,
        }

    def detect_burst_or_persistence(self, entity_id: str, timestamp: datetime) -> dict[str, Any]:
        """Detects high-frequency signal bursts or escalating persistence on a single subject."""
        history = self._entity_signal_history.setdefault(entity_id, [])
        history.append(timestamp)

        # Retain only last 100 entries within 1 hour
        cutoff = timestamp - timedelta(hours=1)
        history[:] = [t for t in history if t >= cutoff]

        recent_burst_cutoff = timestamp - timedelta(seconds=self.burst_window_seconds)
        recent_count = sum(1 for t in history if t >= recent_burst_cutoff)
        is_burst = recent_count >= self.burst_threshold_count

        total_in_hour = len(history)
        is_persistent = total_in_hour >= 10

        return {
            "entity_id": entity_id,
            "is_burst": is_burst,
            "burst_count": recent_count,
            "is_persistent": is_persistent,
            "total_recent_signals": total_in_hour,
        }


# Global instance and legacy alias
signal_correlator = SignalCorrelator()
EventCorrelator = SignalCorrelator
SignalCorrelationEngine = SignalCorrelator
event_correlator = signal_correlator
