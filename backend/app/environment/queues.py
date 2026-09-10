"""Queue Model (Task 54, Prompt #43)."""

from __future__ import annotations

from app.environment.nodes import create_environment_node, generate_canonical_id
from app.environment.schemas import EnvironmentNode, NodeType, ScopeType


class QueueModelManager:
    """Manages message queues and streaming topics (Kafka, RabbitMQ, SQS)."""

    @staticmethod
    def create_queue_node(
        queue_id: str,
        name: str,
        engine: str,  # "kafka", "rabbitmq", "sqs"
        depth: int = 0,
        producers: list[str] | None = None,
        consumers: list[str] | None = None,
        consumer_lag: int = 0,
        health: str = "HEALTHY",
        scope_id: str | None = None,
        source: str = "queue_telemetry",
    ) -> EnvironmentNode:
        canonical = generate_canonical_id(NodeType.QUEUE, f"{engine}:{name}", scope_id=scope_id)
        meta = {
            "queue_name": name,
            "engine": engine,
            "depth": depth,
            "producers": producers or [],
            "consumers": consumers or [],
            "consumer_lag": consumer_lag,
            "health": health,
        }
        return create_environment_node(
            node_id=f"q_{queue_id}",
            node_type=NodeType.QUEUE,
            canonical_id=canonical,
            display_name=f"{name} ({engine})",
            metadata=meta,
            scope=ScopeType.SYSTEM,
            scope_id=scope_id or queue_id,
            status=health,
            provenance={"source": source},
            confidence=0.95,
        )
