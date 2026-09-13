"""Authority Management Engine: discrete authority levels, grants, and least-privilege analysis (Task 78)."""

from __future__ import annotations

import fnmatch
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from app.policy.governance_schemas import (
    AuthorityGrant,
    AuthorityLevel,
    LeastPrivilegeRecommendation,
)

logger = logging.getLogger(__name__)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class AuthorityManagerEngine:
    """Separates authorization from raw technical capability and enforces least-privilege boundaries."""

    def __init__(self) -> None:
        # Map: subject_id -> list[AuthorityGrant]
        self._grants: dict[str, list[AuthorityGrant]] = {}
        self._init_default_system_grant()

    def _init_default_system_grant(self) -> None:
        """Establish baseline system grant for admin operator."""
        self.issue_grant(
            subject_id="system_admin",
            subject_type="USER",
            authority_level=AuthorityLevel.ADMIN,
            allowed_scopes=["*"],
            allowed_actions=["*"],
            granted_by="root",
        )

    def issue_grant(
        self,
        subject_id: str,
        authority_level: AuthorityLevel,
        subject_type: str = "AGENT",
        allowed_scopes: list[str] | None = None,
        allowed_actions: list[str] | None = None,
        denied_actions: list[str] | None = None,
        max_risk_level: str = "R2_MODERATE",
        expires_at: datetime | None = None,
        granted_by: str = "system",
    ) -> AuthorityGrant:
        """Create and register a new discrete authority grant."""
        grant = AuthorityGrant(
            grant_id=f"auth_{uuid.uuid4().hex[:8]}",
            subject_id=subject_id,
            subject_type=subject_type,
            authority_level=authority_level,
            allowed_scopes=allowed_scopes or ["*"],
            allowed_actions=allowed_actions or ["*"],
            denied_actions=denied_actions or [],
            max_risk_level=max_risk_level,
            expires_at=expires_at,
            granted_by=granted_by,
            is_active=True,
            created_at=_now_utc(),
        )
        if subject_id not in self._grants:
            self._grants[subject_id] = []
        self._grants[subject_id].append(grant)
        logger.info("Authority grant issued for subject %s: level=%s", subject_id, authority_level.value)
        return grant

    def revoke_grants(self, subject_id: str) -> int:
        """Deactivate all active authority grants for a subject."""
        grants = self._grants.get(subject_id, [])
        count = 0
        for g in grants:
            if g.is_active:
                g.is_active = False
                count += 1
        return count

    def get_active_grants(self, subject_id: str) -> list[AuthorityGrant]:
        """Return all valid, unexpired authority grants for a subject."""
        now = _now_utc()
        active = []
        for g in self._grants.get(subject_id, []):
            if not g.is_active:
                continue
            if g.expires_at and g.expires_at < now:
                g.is_active = False
                continue
            active.append(g)
        return active

    def get_highest_authority(self, subject_id: str) -> AuthorityLevel:
        """Get the highest active authority level for a subject."""
        grants = self.get_active_grants(subject_id)
        if not grants:
            return AuthorityLevel.NONE
        return max(grants, key=lambda g: g.authority_level.rank).authority_level

    def check_authority(
        self,
        subject_id: str,
        action: str,
        scope: str = "default",
        required_level: AuthorityLevel = AuthorityLevel.LIMITED,
        risk_level: str = "R1_LOW",
    ) -> tuple[bool, str, AuthorityLevel]:
        """Validate whether subject has explicit authority to perform the action.

        Returns (allowed, reason, granted_level).
        """
        grants = self.get_active_grants(subject_id)
        if not grants:
            return False, f"Subject '{subject_id}' has NO active authority grant (NONE)", AuthorityLevel.NONE

        # 1. Check explicit denials first across all grants
        for g in grants:
            for pattern in g.denied_actions:
                if fnmatch.fnmatch(action.lower(), pattern.lower()):
                    return False, f"Action '{action}' explicitly denied by grant '{g.grant_id}'", g.authority_level

        # 2. Find grant satisfying authority level and scope
        highest_level = max(grants, key=lambda g: g.authority_level.rank).authority_level
        if highest_level.rank < required_level.rank:
            return (
                False,
                f"Insufficient authority: action requires {required_level.value} (rank {required_level.rank}), "
                f"but subject only has {highest_level.value} (rank {highest_level.rank})",
                highest_level,
            )

        # 3. Check action and scope matching
        authorized = False
        matching_grant = None
        for g in grants:
            scope_match = any(fnmatch.fnmatch(scope.lower(), s.lower()) for s in g.allowed_scopes)
            action_match = any(fnmatch.fnmatch(action.lower(), a.lower()) for a in g.allowed_actions)
            if scope_match and action_match:
                authorized = True
                matching_grant = g
                break

        if not authorized:
            return False, f"Action '{action}' in scope '{scope}' not permitted under active grants", highest_level

        return True, "Authority verified", matching_grant.authority_level if matching_grant else highest_level

    def analyze_least_privilege(
        self,
        requested_permissions: list[str],
        action: str,
        risk_level: str = "R1_LOW",
    ) -> LeastPrivilegeRecommendation:
        """Perform least-privilege analysis identifying minimal required authority."""
        req_norm = [p.upper() for p in requested_permissions]
        min_needed = []

        # Determine strictly needed permissions based on action verb
        act_lower = action.lower()
        if any(w in act_lower for w in ["read", "get", "list", "fetch", "search", "inspect"]):
            min_needed = ["READ"]
            rec_level = AuthorityLevel.LIMITED
        elif any(w in act_lower for w in ["delete", "remove", "drop", "terminate", "destroy"]):
            min_needed = ["READ", "WRITE", "DESTRUCTIVE"]
            rec_level = AuthorityLevel.PROJECT
        elif any(w in act_lower for w in ["execute", "run", "deploy", "launch"]):
            min_needed = ["READ", "EXECUTE"]
            rec_level = AuthorityLevel.PROJECT
        elif any(w in act_lower for w in ["write", "create", "update", "modify", "patch"]):
            min_needed = ["READ", "WRITE"]
            rec_level = AuthorityLevel.LIMITED
        else:
            min_needed = ["READ", "EXECUTE"]
            rec_level = AuthorityLevel.LIMITED

        excess = [p for p in req_norm if p not in min_needed]
        reduction = len(excess) > 0

        return LeastPrivilegeRecommendation(
            minimum_permissions_needed=min_needed,
            excess_permissions_requested=excess,
            recommended_authority_level=rec_level,
            reduction_possible=reduction,
        )


default_authority_manager = AuthorityManagerEngine()
