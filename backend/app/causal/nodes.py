"""CausalNode creation, canonical identity, and validation (Task 55, Prompt #3)."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from app.causal.schemas import CausalNode
from app.causal.temporal import utc_now


def generate_node_id(entity: str, variable: str) -> str:
    """Generates standardized canonical node ID for an entity variable."""
    e_clean = re.sub(r"\s+", "_", entity.strip().lower())
    v_clean = re.sub(r"\s+", "_", variable.strip().lower())
    return f"cnode_{e_clean}_{v_clean}"


def create_causal_node(
    entity: str,
    variable: str,
    state: Any,
    source: str,
    confidence: float = 1.0,
    timestamp: datetime | None = None,
    node_id: str | None = None,
) -> CausalNode:
    """Instantiates a validated CausalNode."""
    nid = node_id or generate_node_id(entity, variable)
    return CausalNode(
        node_id=nid,
        entity=entity,
        variable=variable,
        state=state,
        timestamp=timestamp or utc_now(),
        source=source,
        confidence=round(max(0.0, min(1.0, confidence)), 2),
    )


create_node = create_causal_node

