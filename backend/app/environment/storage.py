"""Storage Resource Model and Content Protection (Task 54, Prompt #42)."""

from __future__ import annotations

from typing import Any

from app.environment.nodes import create_environment_node, generate_canonical_id
from app.environment.safety import EnvironmentSafetyError
from app.environment.schemas import EnvironmentNode, NodeType, ScopeType


class StorageContentIngestionError(EnvironmentSafetyError):
    """Raised when an attempt is made to ingest raw file or blob contents into storage metadata."""


class StorageModelManager:
    """Manages storage volumes, object buckets, and filestores without ingesting stored data."""

    @staticmethod
    def create_storage_node(
        storage_id: str,
        name: str,
        storage_type: NodeType,  # STORAGE or BUCKET
        capacity_bytes: int,
        used_bytes: int,
        encrypted: bool = True,
        scope_id: str | None = None,
        raw_blob_data: Any = None,
        source: str = "cloud_storage_api",
    ) -> EnvironmentNode:
        # Prompt #42: Represent storage resources without unnecessarily reading contents
        if raw_blob_data is not None:
            raise StorageContentIngestionError(
                "Digital Twin represents storage metadata only; ingesting raw file/blob content is forbidden."
            )

        canonical = generate_canonical_id(storage_type, name, scope_id=scope_id)
        meta = {
            "storage_name": name,
            "capacity_bytes": capacity_bytes,
            "used_bytes": used_bytes,
            "utilization_pct": round((used_bytes / capacity_bytes) * 100, 2) if capacity_bytes > 0 else 0.0,
            "encrypted": encrypted,
        }
        return create_environment_node(
            node_id=f"stor_{storage_id}",
            node_type=storage_type,
            canonical_id=canonical,
            display_name=f"{name} ({storage_type.value})",
            metadata=meta,
            scope=ScopeType.CLOUD,
            scope_id=scope_id or storage_id,
            status="ACTIVE",
            provenance={"source": source},
            confidence=0.98,
        )
