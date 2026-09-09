"""Permission enforcement, capability validation, and risk aggregation for skills."""

import logging
from typing import Any

from app.security.center import SecurityCenter, get_security_center
from app.security.permissions import Capability
from app.security.policies import SecurityDecision
from app.security.risk import TOOL_RISK_MAP, RiskLevel
from app.skills.schemas import SkillManifest, SkillRiskLevel

logger = logging.getLogger("kairo.skills.permissions")

# Map RiskLevel from security subsystem to SkillRiskLevel
_SECURITY_TO_SKILL_RISK: dict[RiskLevel, SkillRiskLevel] = {
    RiskLevel.LOW: SkillRiskLevel.LOW,
    RiskLevel.MEDIUM: SkillRiskLevel.MEDIUM,
    RiskLevel.HIGH: SkillRiskLevel.HIGH,
    RiskLevel.CRITICAL: SkillRiskLevel.CRITICAL,
}


class SkillPermissionEnforcer:
    """Enforces SecurityCenter capability gates, project ownership, and risk aggregation."""

    def __init__(self, security_center: SecurityCenter | None = None) -> None:
        self.security_center = security_center or get_security_center()

    def aggregate_skill_risk(self, manifest: SkillManifest) -> SkillRiskLevel:
        """Compute minimum aggregated risk level across all required and optional tools.

        Guarantees that a skill cannot downgrade any underlying tool risk.
        """
        tool_names = set(manifest.required_tools + manifest.optional_tools)
        risks = [manifest.risk_level]

        for t_name in tool_names:
            if t_name in TOOL_RISK_MAP:
                sec_risk = TOOL_RISK_MAP[t_name]
                risks.append(_SECURITY_TO_SKILL_RISK.get(sec_risk, SkillRiskLevel.LOW))

        computed_max = SkillRiskLevel.max_risk(risks)
        return computed_max

    async def authorize_skill_execution(
        self,
        manifest: SkillManifest,
        user_id: str,
        inputs: dict[str, Any],
        project_id: str | None = None,
        device_id: str | None = None,
        session_id: str | None = None,
        db_session: Any = None,
    ) -> tuple[bool, str | None, bool]:
        """Verify authorization through SecurityCenter before executing a skill.

        Returns: (allowed: bool, reason: str | None, approval_required: bool)
        """
        # 1. Project ownership check if skill is project_scoped
        if manifest.project_scoped:
            if not project_id:
                return False, f"Skill '{manifest.id}' requires an active project context.", False
            # Verify project access if db_session available
            if db_session is not None:
                from sqlalchemy import and_, select

                from app.models.project import Project

                stmt = select(Project).where(and_(Project.id == project_id, Project.user_id == user_id))
                res = await db_session.execute(stmt)
                if not res.scalar_one_or_none():
                    return (
                        False,
                        f"Access denied: Project '{project_id}' not found or belongs to another user.",
                        False,
                    )

        # 2. Device scoping check if skill is device_scoped
        if manifest.device_scoped:
            if not device_id:
                return False, f"Skill '{manifest.id}' requires an explicit device binding (device_id).", False

        # 3. Check capability gates for all declared capabilities
        for cap_str in manifest.capabilities:
            try:
                cap_enum = Capability(cap_str)
                if not await self.security_center.is_capability_enabled(db_session, user_id, cap_enum):
                    return False, f"Capability gate '{cap_str}' is disabled in SecurityCenter.", False
            except ValueError:
                logger.warning("Unknown capability declared in skill manifest: %s", cap_str)

        # 4. Check emergency stop
        if self.security_center.is_emergency_stopped(user_id):
            return False, "Execution blocked: Emergency Stop is currently active.", False

        # 5. Risk and approval evaluation
        agg_risk = self.aggregate_skill_risk(manifest)
        if agg_risk in (SkillRiskLevel.CRITICAL, SkillRiskLevel.DESTRUCTIVE):
            return (
                False,
                f"Skill '{manifest.id}' is strictly prohibited by security policy ({agg_risk.value}).",
                False,
            )

        if agg_risk == SkillRiskLevel.HIGH:
            # Check if active approval exists for this exact skill execution fingerprint
            if db_session is not None:
                from app.security.approvals import ApprovalManager
                from app.security.redaction import ArgumentSanitizer

                fingerprint = ArgumentSanitizer.compute_action_fingerprint(
                    tool_name=manifest.id,
                    user_id=user_id,
                    session_id=session_id,
                    arguments=inputs,
                )
                active_approval = await ApprovalManager.find_active_approval(
                    db_session=db_session,
                    user_id=user_id,
                    action_fingerprint=fingerprint,
                )
                if active_approval:
                    return True, None, False

            return True, "Explicit user approval required for high-risk skill.", True

        return True, None, False
