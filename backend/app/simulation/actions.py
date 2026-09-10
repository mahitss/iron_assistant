"""Sandboxed simulation actions.

All actions execute purely in memory and manipulate hypothetical simulation models.
Calls to production ToolExecutor, shell, network, or databases are strictly prohibited.
"""

from __future__ import annotations

import copy
from typing import Any

from app.simulation.safety import block_production_side_effects


class BaseSandboxedAction:
    """Base class for all simulated actions."""

    name: str = "base_action"

    def execute(self, state: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        """Executes the action on the in-memory simulation state."""
        block_production_side_effects(self.name, kwargs.get("target"))
        raise NotImplementedError


class RestartServiceAction(BaseSandboxedAction):
    name = "SIMULATED_RESTART_SERVICE"

    def execute(self, state: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        service_name = kwargs.get("service_name", "unknown")
        block_production_side_effects(self.name, service_name)
        new_state = copy.deepcopy(state)
        services = new_state.setdefault("services", {})
        svc = services.setdefault(service_name, {})
        svc["status"] = "RESTARTING"
        svc["restarts"] = svc.get("restarts", 0) + 1
        svc["health"] = "HEALTHY"
        return new_state


class KillServiceAction(BaseSandboxedAction):
    name = "SIMULATED_KILL_SERVICE"

    def execute(self, state: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        service_name = kwargs.get("service_name", "unknown")
        block_production_side_effects(self.name, service_name)
        new_state = copy.deepcopy(state)
        services = new_state.setdefault("services", {})
        svc = services.setdefault(service_name, {})
        svc["status"] = "DEAD"
        svc["health"] = "CRITICAL"
        return new_state


class UpdateConfigAction(BaseSandboxedAction):
    name = "SIMULATED_UPDATE_CONFIG"

    def execute(self, state: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        config_key = kwargs.get("key", "default")
        config_val = kwargs.get("value")
        block_production_side_effects(self.name, config_key)
        new_state = copy.deepcopy(state)
        configs = new_state.setdefault("configs", {})
        configs[config_key] = config_val
        return new_state


class ScaleReplicasAction(BaseSandboxedAction):
    name = "SIMULATED_SCALE_REPLICAS"

    def execute(self, state: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        service_name = kwargs.get("service_name", "unknown")
        replicas = int(kwargs.get("replicas", 1))
        block_production_side_effects(self.name, service_name)
        new_state = copy.deepcopy(state)
        services = new_state.setdefault("services", {})
        svc = services.setdefault(service_name, {})
        svc["replicas"] = replicas
        return new_state


class ShiftTrafficAction(BaseSandboxedAction):
    name = "SIMULATED_SHIFT_TRAFFIC"

    def execute(self, state: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        source = kwargs.get("source", "blue")
        target = kwargs.get("target", "green")
        percent = float(kwargs.get("percentage", 100.0))
        block_production_side_effects(self.name, f"{source}->{target}")
        new_state = copy.deepcopy(state)
        routing = new_state.setdefault("traffic_routing", {})
        routing[source] = max(0.0, 100.0 - percent)
        routing[target] = percent
        return new_state


class RollbackVersionAction(BaseSandboxedAction):
    name = "SIMULATED_ROLLBACK_VERSION"

    def execute(self, state: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        service_name = kwargs.get("service_name", "unknown")
        target_version = kwargs.get("target_version", "previous")
        block_production_side_effects(self.name, service_name)
        new_state = copy.deepcopy(state)
        deployments = new_state.setdefault("deployments", {})
        dep = deployments.setdefault(service_name, {})
        dep["version"] = target_version
        dep["status"] = "ROLLED_BACK"
        return new_state


class FailoverDatabaseAction(BaseSandboxedAction):
    name = "SIMULATED_FAILOVER_DATABASE"

    def execute(self, state: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        cluster_name = kwargs.get("cluster_name", "primary_cluster")
        target_replica = kwargs.get("target_replica", "replica_1")
        block_production_side_effects(self.name, cluster_name)
        new_state = copy.deepcopy(state)
        db_state = new_state.setdefault("databases", {})
        cl = db_state.setdefault(cluster_name, {})
        cl["primary"] = target_replica
        cl["failover_count"] = cl.get("failover_count", 0) + 1
        return new_state


class InjectLatencyAction(BaseSandboxedAction):
    name = "SIMULATED_INJECT_LATENCY"

    def execute(self, state: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        node = kwargs.get("node", "gateway")
        added_ms = float(kwargs.get("latency_ms", 100.0))
        block_production_side_effects(self.name, node)
        new_state = copy.deepcopy(state)
        network = new_state.setdefault("network_latency", {})
        current = network.get(node, 10.0)
        network[node] = current + added_ms
        return new_state


ACTION_REGISTRY: dict[str, type[BaseSandboxedAction]] = {
    "RESTART_SERVICE": RestartServiceAction,
    "KILL_SERVICE": KillServiceAction,
    "UPDATE_CONFIG": UpdateConfigAction,
    "SCALE_REPLICAS": ScaleReplicasAction,
    "SHIFT_TRAFFIC": ShiftTrafficAction,
    "ROLLBACK_VERSION": RollbackVersionAction,
    "FAILOVER_DATABASE": FailoverDatabaseAction,
    "INJECT_LATENCY": InjectLatencyAction,
}
