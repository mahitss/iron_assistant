"""EnvironmentNode model manager, canonical ID generation, and validation (Task 54)."""

from __future__ import annotations

import re
from typing import Any

from app.environment.safety import EnvironmentSafetyGuard, SecretStorageViolationError
from app.environment.schemas import EnvironmentNode, NodeType, ScopeType
from app.environment.temporal import utc_now


def generate_canonical_id(node_type: NodeType, identifier: str, scope_id: str | None = None) -> str:
    """Produces standardized canonical identifiers to ensure idempotent resolution and deduplication."""
    clean_id = re.sub(r"\s+", "_", identifier.strip().lower())
    prefix = node_type.value.lower()
    if scope_id:
        clean_scope = re.sub(r"\s+", "_", scope_id.strip().lower())
        return f"{prefix}:{clean_scope}:{clean_id}"
    return f"{prefix}:{clean_id}"


def create_environment_node(
    node_id: str,
    node_type: NodeType,
    canonical_id: str,
    display_name: str,
    metadata: dict[str, Any] | None = None,
    scope: ScopeType = ScopeType.SYSTEM,
    scope_id: str | None = None,
    status: str = "UNKNOWN",
    provenance: dict[str, Any] | None = None,
    confidence: float = 1.0,
) -> EnvironmentNode:
    """Creates a validated, sanitized EnvironmentNode."""
    raw_meta = metadata or {}

    # Prompt #6, #52, #187: SECRET_REFERENCE without storing secret values
    if node_type == NodeType.SECRET_REFERENCE:
        if "secret_value" in raw_meta or "value" in raw_meta:
            raise SecretStorageViolationError(
                "SECRET_REFERENCE nodes must not contain secret values, only references/names."
            )

    # Sanitize metadata to prevent secret leakage
    sanitized_metadata = EnvironmentSafetyGuard.inspect_and_sanitize_metadata(raw_meta, raise_on_secret=True)

    now = utc_now()
    return EnvironmentNode(
        node_id=node_id,
        node_type=node_type,
        canonical_id=canonical_id,
        display_name=display_name,
        metadata=sanitized_metadata,
        scope=scope,
        scope_id=scope_id,
        status=status,
        first_seen=now,
        last_seen=now,
        provenance=provenance or {"source": "manual", "observed_at": now.isoformat()},
        confidence=confidence,
    )
