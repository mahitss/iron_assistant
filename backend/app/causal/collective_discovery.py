"""Collective Causal Discovery & Dissent Preservation Engine (Task 73, Spec 43, 44).

Strict Invariant:
Preserve competing models when agents or sources disagree.
Consensus is NOT proof. Do not discard minority causal models until empirical evidence disproves them.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from app.causal.discovery_schemas import CausalRelationship

logger = logging.getLogger(__name__)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class CausalConflictRecord:
    """Represents a conflict or dissent between competing causal explanations."""

    def __init__(
        self,
        conflict_id: str,
        effect_entity: str,
        effect_variable: str,
        competing_relationships: list[CausalRelationship],
        dissenting_agents: list[str],
        status: str = "ACTIVE_DISSENT",
    ) -> None:
        self.conflict_id = conflict_id
        self.effect_entity = effect_entity
        self.effect_variable = effect_variable
        self.competing_relationships = competing_relationships
        self.dissenting_agents = dissenting_agents
        self.status = status
        self.created_at = _now_utc()

    def to_dict(self) -> dict[str, Any]:
        return {
            "conflict_id": self.conflict_id,
            "effect_entity": self.effect_entity,
            "effect_variable": self.effect_variable,
            "competing_relationship_ids": [r.causal_relation_id for r in self.competing_relationships],
            "dissenting_agents": self.dissenting_agents,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
        }


class CollectiveCausalDiscoveryEngine:
    """Manages multi-agent proposed causal hypotheses and retains competing explanations."""

    def __init__(self) -> None:
        self._conflicts: dict[str, CausalConflictRecord] = {}

    def register_agent_hypothesis(
        self,
        relationship: CausalRelationship,
        agent_id: str,
        existing_relationships: list[CausalRelationship],
    ) -> CausalConflictRecord | None:
        """Evaluate if an incoming agent-proposed relationship conflicts with existing models."""
        target_entity = relationship.effect_entity
        target_var = relationship.effect_variable

        # Find existing relationships for same effect with different causes
        conflicting: list[CausalRelationship] = []
        for ex in existing_relationships:
            if (
                ex.effect_entity == target_entity
                and ex.effect_variable == target_var
                and (ex.cause_entity != relationship.cause_entity or ex.cause_variable != relationship.cause_variable)
            ):
                conflicting.append(ex)

        if conflicting:
            all_competing = conflicting + [relationship]
            conflict_id = f"conf_{uuid.uuid4().hex[:8]}"
            agents = list(
                {
                    ex.provenance.get("agent_id", "AGENT_A") for ex in conflicting
                }
            )
            agents.append(agent_id)

            record = CausalConflictRecord(
                conflict_id=conflict_id,
                effect_entity=target_entity,
                effect_variable=target_var,
                competing_relationships=all_competing,
                dissenting_agents=agents,
                status="ACTIVE_DISSENT",
            )
            self._conflicts[conflict_id] = record
            logger.info(
                f"Causal Dissent Preserved: Agents {agents} proposed competing causes for "
                f"{target_entity}:{target_var}. Preserving both models."
            )
            return record

        return None

    def get_conflicts(self) -> list[dict[str, Any]]:
        """Retrieve all active competing causal models."""
        return [c.to_dict() for c in self._conflicts.values()]
