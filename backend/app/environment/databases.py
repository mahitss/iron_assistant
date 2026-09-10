"""Database Model and Content Protection (Task 54, Prompts #23, #24)."""

from __future__ import annotations

from typing import Any

from app.environment.nodes import create_environment_node, generate_canonical_id
from app.environment.safety import EnvironmentSafetyError
from app.environment.schemas import EnvironmentNode, NodeType, ScopeType


class DatabaseContentIngestionError(EnvironmentSafetyError):
    """Raised when an attempt is made to ingest database table contents into the digital twin."""


class DatabaseModelManager:
    """Represents databases while preventing ingestion of user/table contents."""

    @staticmethod
    def create_database_node(
        database_id: str,
        name: str,
        engine: str,  # PostgreSQL, MySQL, Redis, MongoDB
        version: str,
        environment: str,
        endpoint_ref: str,  # ref://endpoints/db-prod-1
        status: str = "ONLINE",
        table_count: int | None = None,
        scope_id: str | None = None,
        raw_content_payload: Any = None,
        source: str = "db_admin_api",
    ) -> EnvironmentNode:
        # Prompt #24: Do not ingest database contents unless explicitly required and authorized
        if raw_content_payload is not None:
            raise DatabaseContentIngestionError(
                "Digital Twin is forbidden from ingesting raw database table records/contents."
            )

        canonical = generate_canonical_id(NodeType.DATABASE, f"{engine}:{name}", scope_id=environment)
        meta = {
            "database_name": name,
            "engine": engine,
            "version": version,
            "environment": environment,
            "endpoint_ref": endpoint_ref,
            "table_count": table_count or 0,
        }
        return create_environment_node(
            node_id=f"db_{database_id}",
            node_type=NodeType.DATABASE,
            canonical_id=canonical,
            display_name=f"{name} ({engine} {version})",
            metadata=meta,
            scope=ScopeType.ENVIRONMENT,
            scope_id=scope_id or environment,
            status=status,
            provenance={"source": source, "collector": "db_metadata_collector"},
            confidence=0.98,
        )
