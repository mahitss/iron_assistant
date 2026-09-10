"""Process Model and Process Privacy controls (Task 54, Prompts #17, #18, #183)."""

from __future__ import annotations

from app.environment.nodes import create_environment_node, generate_canonical_id
from app.environment.safety import UnauthorizedDiscoveryError
from app.environment.schemas import EnvironmentNode, NodeType, ScopeType

# Authorized process prefixes / names for Kairo monitoring scope
DEFAULT_AUTHORIZED_PROCESSES = {
    "python", "python3", "uvicorn", "gunicorn", "node", "npm", "postgres",
    "redis-server", "nginx", "docker", "dockerd", "containerd", "kubelet"
}


class ProcessModelManager:
    """Manages process modeling with strict privacy and scope boundaries."""

    @staticmethod
    def create_process_node(
        pid: int,
        name: str,
        host_id: str,
        status: str = "RUNNING",
        cpu_percent: float = 0.0,
        memory_mb: float = 0.0,
        start_time: str | None = None,
        authorized_names: set[str] | None = None,
        source: str = "os_telemetry",
    ) -> EnvironmentNode:
        # Prompt #18, #183: Only inspect processes within authorized scope
        allowed = authorized_names or DEFAULT_AUTHORIZED_PROCESSES
        base_name = name.lower().split(".exe")[0]
        if base_name not in allowed and not any(base_name.startswith(p) for p in allowed):
            raise UnauthorizedDiscoveryError(
                f"Inspection of process '{name}' (PID {pid}) on host '{host_id}' is outside authorized scope."
            )

        canonical = generate_canonical_id(NodeType.PROCESS, f"{host_id}:{pid}:{name}")
        meta = {
            "pid": pid,
            "name": name,
            "host_id": host_id,
            "cpu_percent": cpu_percent,
            "memory_mb": memory_mb,
            "start_time": start_time or "unknown",
        }
        return create_environment_node(
            node_id=f"proc_{host_id}_{pid}",
            node_type=NodeType.PROCESS,
            canonical_id=canonical,
            display_name=f"{name} (PID {pid})",
            metadata=meta,
            scope=ScopeType.HOST,
            scope_id=host_id,
            status=status,
            provenance={"source": source, "collector": "process_agent"},
            confidence=0.95,
        )
