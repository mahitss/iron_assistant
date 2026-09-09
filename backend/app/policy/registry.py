"""Policy Registry with Versioning, History, Shadow Mode, and Cache (Task 36).

Ensures:
- Policies are strictly versioned upon any mutation.
- Rollback to prior versions is fully supported.
- Shadow mode policies evaluate without enforcing.
- Safe deterministic caching with immediate invalidation hooks.
"""

from collections import OrderedDict
from datetime import UTC, datetime
import hashlib
import json
import logging
from typing import Any

from app.policy.rules import DEFAULT_SYSTEM_POLICIES
from app.policy.schemas import (
    PolicyContext,
    PolicyCreateRequest,
    PolicyDecision,
    PolicyRollbackRequest,
    PolicyRule,
    PolicyUpdateRequest,
)

logger = logging.getLogger("kairo.policy.registry")


class PolicyRegistry:
    """In-memory and persisted registry of governance policies with versioning."""

    def __init__(self) -> None:
        # policy_id -> current PolicyRule
        self._policies: dict[str, PolicyRule] = {}
        # policy_id -> dict[version, PolicyRule] (version history)
        self._history: dict[str, dict[int, PolicyRule]] = {}
        # Simple LRU cache for deterministic policy evaluations
        self._decision_cache: OrderedDict[str, PolicyDecision] = OrderedDict()
        self._cache_max_size = 500

        # Load baseline system policies
        for p in DEFAULT_SYSTEM_POLICIES:
            self.register_policy(p)

    def register_policy(self, rule: PolicyRule) -> PolicyRule:
        """Register a policy and record its version history."""
        self._validate_policy(rule)
        self._policies[rule.policy_id] = rule

        if rule.policy_id not in self._history:
            self._history[rule.policy_id] = {}
        self._history[rule.policy_id][rule.version] = rule

        self.invalidate_cache()
        return rule

    def create_policy(self, req: PolicyCreateRequest, creator: str | None = None) -> PolicyRule:
        """Create a new policy (version 1)."""
        if req.policy_id in self._policies:
            raise ValueError(f"Policy with ID '{req.policy_id}' already exists")

        now = datetime.now(UTC)
        rule = PolicyRule(
            policy_id=req.policy_id,
            name=req.name,
            description=req.description,
            version=1,
            enabled=True,
            is_system=False,
            shadow_mode=req.shadow_mode,
            priority=req.priority,
            scope=req.scope,
            target_scope_id=req.target_scope_id,
            conditions=req.conditions,
            decision=req.decision,
            reason_code=req.reason_code,
            safe_explanation=req.safe_explanation,
            constraints=req.constraints,
            created_by=creator,
            created_at=now,
            updated_at=now,
        )
        return self.register_policy(rule)

    def update_policy(self, policy_id: str, req: PolicyUpdateRequest, updater: str | None = None) -> PolicyRule:
        """Update a policy by creating a new incremented version (Section 7)."""
        existing = self.get_policy(policy_id)
        if not existing:
            raise KeyError(f"Policy '{policy_id}' not found")

        if existing.is_system and req.enabled is False:
            raise PermissionError("System core policies cannot be disabled")

        now = datetime.now(UTC)
        new_version = existing.version + 1

        updated_rule = PolicyRule(
            policy_id=policy_id,
            name=req.name if req.name is not None else existing.name,
            description=req.description if req.description is not None else existing.description,
            version=new_version,
            enabled=req.enabled if req.enabled is not None else existing.enabled,
            is_system=existing.is_system,
            shadow_mode=req.shadow_mode if req.shadow_mode is not None else existing.shadow_mode,
            priority=req.priority if req.priority is not None else existing.priority,
            scope=existing.scope,
            target_scope_id=existing.target_scope_id,
            conditions=req.conditions if req.conditions is not None else existing.conditions,
            decision=req.decision if req.decision is not None else existing.decision,
            reason_code=req.reason_code if req.reason_code is not None else existing.reason_code,
            safe_explanation=req.safe_explanation if req.safe_explanation is not None else existing.safe_explanation,
            constraints=req.constraints if req.constraints is not None else existing.constraints,
            created_by=updater or existing.created_by,
            created_at=existing.created_at,
            updated_at=now,
        )
        return self.register_policy(updated_rule)

    def rollback_policy(self, policy_id: str, req: PolicyRollbackRequest, operator: str | None = None) -> PolicyRule:
        """Roll back a policy to a prior version (Section 154)."""
        if policy_id not in self._history or req.target_version not in self._history[policy_id]:
            raise KeyError(f"Version {req.target_version} not found for policy '{policy_id}'")

        target_past_rule = self._history[policy_id][req.target_version]
        now = datetime.now(UTC)
        current = self._policies[policy_id]
        new_version = current.version + 1

        rollback_rule = target_past_rule.model_copy(
            update={
                "version": new_version,
                "description": f"{target_past_rule.description} (Rolled back to v{req.target_version}: {req.reason})",
                "created_by": operator or "system_admin",
                "updated_at": now,
            }
        )
        return self.register_policy(rollback_rule)

    def get_policy(self, policy_id: str) -> PolicyRule | None:
        """Fetch active policy by ID."""
        return self._policies.get(policy_id)

    def get_policy_version(self, policy_id: str, version: int) -> PolicyRule | None:
        """Fetch specific historical version of policy."""
        return self._history.get(policy_id, {}).get(version)

    def list_policies(self, include_disabled: bool = True) -> list[PolicyRule]:
        """List all active registered policies."""
        if include_disabled:
            return list(self._policies.values())
        return [p for p in self._policies.values() if p.enabled]

    def get_history(self, policy_id: str) -> list[PolicyRule]:
        """Return all historical versions of a policy."""
        if policy_id not in self._history:
            return []
        return sorted(self._history[policy_id].values(), key=lambda p: p.version)

    # ==========================================
    # Evaluation Cache
    # ==========================================

    def get_cached_decision(self, context: PolicyContext) -> PolicyDecision | None:
        """Fetch cached evaluation decision if exists and valid."""
        cache_key = self._generate_cache_key(context)
        if cache_key in self._decision_cache:
            dec = self._decision_cache[cache_key]
            # Check expiration
            if dec.expires_at and datetime.now(UTC) > dec.expires_at:
                del self._decision_cache[cache_key]
                return None
            return dec
        return None

    def cache_decision(self, context: PolicyContext, decision: PolicyDecision) -> None:
        """Cache deterministic decision for non-critical reads."""
        # Never cache high or critical risk decisions (Section 94, 95)
        if decision.risk_level.severity >= 3:
            return

        cache_key = self._generate_cache_key(context)
        self._decision_cache[cache_key] = decision
        if len(self._decision_cache) > self._cache_max_size:
            self._decision_cache.popitem(last=False)

    def invalidate_cache(self) -> None:
        """Clear the decision cache immediately on any policy or environment change (Section 93)."""
        self._decision_cache.clear()

    @property
    def cached_count(self) -> int:
        return len(self._decision_cache)

    # ==========================================
    # Helpers
    # ==========================================

    def _validate_policy(self, rule: PolicyRule) -> None:
        """Validate policy syntax, fields, and operators (Section 86)."""
        if not rule.policy_id or not rule.name:
            raise ValueError("Policy must have a valid policy_id and name")
        for cond in rule.conditions:
            if not cond.field or not cond.operator:
                raise ValueError(f"Invalid condition in policy '{rule.policy_id}': field and operator required")

    def _generate_cache_key(self, context: PolicyContext) -> str:
        """Create a deterministic hash key for safe decision caching."""
        user_id = (context.user or {}).get("id", "")
        env = context.environment or ""
        action = context.action or ""
        target_str = str(context.target or "")
        key_raw = f"{user_id}|{env}|{action}|{target_str}"
        return hashlib.sha256(key_raw.encode("utf-8")).hexdigest()


# Global policy registry singleton
policy_registry = PolicyRegistry()
