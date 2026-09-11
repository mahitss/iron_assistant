"""Synthetic environment fixtures for Task 76 Resilience & Recovery testing.

Provides 10 deterministic environments (Section 71):
1. healthy redundant system
2. single point of failure
3. deep dependency chain
4. cascading failure
5. recoverable outage
6. unrecoverable outage
7. partial recovery
8. failed rollback
9. degraded mode
10. human-required recovery
"""

from typing import Any


def fixture_healthy_redundant_system() -> dict[str, Any]:
    """1. Healthy redundant cluster with active and passive backups across all critical tiers."""
    return {
        "nodes": {
            "web_lb": {
                "criticality": 0.8,
                "scope": "EDGE",
                "has_redundancy": True,
                "backups": [{"id": "web_lb_secondary", "mode": "active"}],
                "has_circuit_breaker": True,
                "isolation_supported": True,
                "recoverable": True,
                "has_rollback": True,
                "has_health_check": True,
                "metrics_reported": True,
                "resource_headroom": 0.65,
                "recovery_time_seconds": 10.0,
            },
            "auth_service": {
                "criticality": 0.9,
                "scope": "AUTH",
                "has_redundancy": True,
                "backups": [{"id": "auth_replica", "mode": "active"}],
                "has_circuit_breaker": True,
                "isolation_supported": True,
                "recoverable": True,
                "has_rollback": True,
                "has_health_check": True,
                "metrics_reported": True,
                "resource_headroom": 0.7,
                "recovery_time_seconds": 15.0,
            },
            "db_primary": {
                "criticality": 0.95,
                "scope": "DATA",
                "has_redundancy": True,
                "backups": [{"id": "db_standby", "mode": "passive"}],
                "has_circuit_breaker": True,
                "isolation_supported": True,
                "recoverable": True,
                "has_rollback": True,
                "has_health_check": True,
                "metrics_reported": True,
                "resource_headroom": 0.8,
                "recovery_time_seconds": 20.0,
            },
        },
        "edges": [
            {"source": "web_lb", "target": "auth_service"},
            {"source": "auth_service", "target": "db_primary"},
        ],
        "spofs": [],
        "bottlenecks": [],
    }


def fixture_single_point_of_failure() -> dict[str, Any]:
    """2. System with a high-fanout single point of failure without backup."""
    return {
        "nodes": {
            "shared_redis": {
                "criticality": 0.95,
                "scope": "CACHE",
                "has_redundancy": False,
                "backups": [],
                "has_circuit_breaker": False,
                "isolation_supported": False,
                "recoverable": True,
                "has_rollback": False,
                "has_health_check": True,
                "metrics_reported": True,
                "resource_headroom": 0.1,
                "recovery_time_seconds": 90.0,
            },
            "svc_a": {"criticality": 0.7, "has_redundancy": False},
            "svc_b": {"criticality": 0.7, "has_redundancy": False},
            "svc_c": {"criticality": 0.8, "has_redundancy": False},
        },
        "edges": [
            {"source": "shared_redis", "target": "svc_a"},
            {"source": "shared_redis", "target": "svc_b"},
            {"source": "shared_redis", "target": "svc_c"},
        ],
        "spofs": ["shared_redis"],
        "bottlenecks": ["shared_redis"],
    }


def fixture_deep_dependency_chain() -> dict[str, Any]:
    """3. Deep serial dependency chain: A -> B -> C -> D -> E."""
    entities = ["edge_proxy", "api_gateway", "biz_logic", "data_layer", "storage_san"]
    nodes = {}
    for idx, e in enumerate(entities):
        nodes[e] = {
            "criticality": 0.5 + (idx * 0.1),
            "scope": f"TIER_{idx}",
            "has_redundancy": idx == 0,
            "has_circuit_breaker": idx in (1, 2),
            "isolation_supported": True,
            "recoverable": True,
            "has_rollback": True,
            "recovery_time_seconds": 20.0 + (idx * 10),
        }
    edges = [{"source": entities[i], "target": entities[i+1]} for i in range(len(entities)-1)]
    return {"nodes": nodes, "edges": edges, "spofs": [entities[2], entities[3]], "bottlenecks": [entities[3]]}


def fixture_cascading_failure() -> dict[str, Any]:
    """4. Cascading instability propagating across interconnected nodes."""
    return {
        "nodes": {
            "ingress": {"criticality": 0.85, "has_circuit_breaker": False, "isolation_supported": False},
            "order_service": {"criticality": 0.9, "has_circuit_breaker": False, "isolation_supported": False},
            "payment_gateway": {"criticality": 0.95, "has_circuit_breaker": True, "isolation_supported": True},
            "notification_bus": {"criticality": 0.6, "has_circuit_breaker": False, "isolation_supported": False},
        },
        "edges": [
            {"source": "ingress", "target": "order_service"},
            {"source": "order_service", "target": "payment_gateway"},
            {"source": "order_service", "target": "notification_bus"},
        ],
        "spofs": ["ingress", "order_service"],
        "bottlenecks": ["order_service"],
    }


def fixture_recoverable_outage() -> dict[str, Any]:
    """5. Outage on service with proven automated failover and rollback."""
    return {
        "nodes": {
            "user_api": {
                "criticality": 0.8,
                "has_redundancy": True,
                "backups": [{"id": "user_api_backup", "mode": "active"}],
                "has_rollback": True,
                "recoverable": True,
                "recovery_time_seconds": 15.0,
            }
        },
        "edges": [],
        "spofs": [],
        "bottlenecks": [],
    }


def fixture_unrecoverable_outage() -> dict[str, Any]:
    """6. Catastrophic state failure with no backup, no rollback, and high uncertainty."""
    return {
        "nodes": {
            "legacy_core": {
                "criticality": 0.98,
                "has_redundancy": False,
                "has_rollback": False,
                "recoverable": False,
                "recovery_time_seconds": 3600.0,
            }
        },
        "edges": [],
        "spofs": ["legacy_core"],
        "bottlenecks": ["legacy_core"],
    }


def fixture_partial_recovery() -> dict[str, Any]:
    """7. Environment where core recovers but downstream cache/worker remains degraded."""
    return {
        "nodes": {
            "core_db": {"criticality": 0.9, "has_redundancy": True, "recoverable": True},
            "analytics_worker": {"criticality": 0.4, "has_redundancy": False, "recoverable": False},
        },
        "edges": [{"source": "core_db", "target": "analytics_worker"}],
        "spofs": [],
        "bottlenecks": [],
    }


def fixture_failed_rollback() -> dict[str, Any]:
    """8. Scenario with broken rollback snapshot triggering rollback verification failure."""
    return {
        "nodes": {
            "corrupted_node": {
                "criticality": 0.85,
                "has_rollback": True,
                "has_redundancy": False,
                "rollback_corrupted": True,
            }
        },
        "edges": [],
        "spofs": ["corrupted_node"],
        "bottlenecks": [],
    }


def fixture_degraded_mode() -> dict[str, Any]:
    """9. System with explicit support for fallback degraded operation."""
    return {
        "nodes": {
            "recommendation_engine": {
                "criticality": 0.5,
                "supports_degraded_mode": True,
                "has_redundancy": False,
                "recoverable": True,
            }
        },
        "edges": [],
        "spofs": [],
        "bottlenecks": [],
    }


def fixture_human_required_recovery() -> dict[str, Any]:
    """10. Severe ambiguous outage with high uncertainty and irreversible mutations requiring human intervention."""
    return {
        "nodes": {
            "billing_ledger": {
                "criticality": 1.0,
                "has_redundancy": False,
                "has_rollback": False,
                "recoverable": False,
                "high_uncertainty": True,
            }
        },
        "edges": [],
        "spofs": ["billing_ledger"],
        "bottlenecks": ["billing_ledger"],
    }
