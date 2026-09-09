"""Dynamic service map and dependency graph generation from telemetry (Task 38)."""

import threading
from datetime import UTC, datetime
from collections import defaultdict
from typing import Any

from app.observability.schemas import (
    DependencyEdge,
    DependencyHealthState,
    DependencyNode,
    ServiceMap,
)


class DependencyGraphTracker:
    """Derives live logical service topology and component health from actual span telemetry."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._calls: dict[tuple[str, str], int] = defaultdict(int)
        self._errors: dict[tuple[str, str], int] = defaultdict(int)
        self._latencies: dict[str, list[float]] = defaultdict(list)
        self._node_types: dict[str, str] = {
            "frontend": "ui",
            "api": "api",
            "task_engine": "orchestrator",
            "agent": "agent",
            "skill": "skill",
            "tool": "tool",
            "model_router": "router",
            "provider": "external_model",
            "database": "datastore",
            "redis": "cache",
            "event_bus": "messaging",
        }

    def record_call(self, source: str, target: str, duration_ms: float = 10.0, is_error: bool = False) -> None:
        """Records an observed invocation between two components."""
        with self._lock:
            key = (source, target)
            self._calls[key] += 1
            if is_error:
                self._errors[key] += 1
            self._latencies[target].append(duration_ms)
            if len(self._latencies[target]) > 500:
                self._latencies[target] = self._latencies[target][-250:]

    def generate_service_map(self) -> ServiceMap:
        """Generates dynamic ServiceMap from observed telemetry."""
        with self._lock:
            nodes_dict: dict[str, DependencyNode] = {}
            edges: list[DependencyEdge] = []

            # 1. Build edges and collect discovered nodes
            for (source, target), call_count in self._calls.items():
                err_count = self._errors.get((source, target), 0)
                edges.append(
                    DependencyEdge(
                        source=source,
                        target=target,
                        call_count=call_count,
                        error_count=err_count,
                    )
                )

                # Register nodes
                for name in (source, target):
                    if name not in nodes_dict:
                        node_type = self._node_types.get(name, "component")
                        latencies = self._latencies.get(name, [0.0])
                        p95 = sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0.0

                        # Calculate node-level error rate
                        total_in = sum(cnt for (s, t), cnt in self._calls.items() if t == name)
                        err_in = sum(ecnt for (s, t), ecnt in self._errors.items() if t == name)
                        err_rate = (err_in / total_in) if total_in > 0 else 0.0

                        health = DependencyHealthState.HEALTHY
                        if err_rate >= 0.5:
                            health = DependencyHealthState.UNAVAILABLE
                        elif err_rate >= 0.1 or p95 > 2000.0:
                            health = DependencyHealthState.DEGRADED

                        nodes_dict[name] = DependencyNode(
                            name=name,
                            type=node_type,
                            health=health,
                            latency_p95_ms=round(p95, 2),
                            error_rate=round(err_rate, 4),
                        )

            # Ensure standard baseline nodes exist
            for base_node, n_type in self._node_types.items():
                if base_node not in nodes_dict:
                    nodes_dict[base_node] = DependencyNode(
                        name=base_node,
                        type=n_type,
                        health=DependencyHealthState.HEALTHY,
                        latency_p95_ms=1.0,
                        error_rate=0.0,
                    )

            return ServiceMap(
                nodes=list(nodes_dict.values()),
                edges=edges,
                generated_at=datetime.now(UTC),
            )

    def clear(self) -> None:
        with self._lock:
            self._calls.clear()
            self._errors.clear()
            self._latencies.clear()


dependency_tracker = DependencyGraphTracker()
