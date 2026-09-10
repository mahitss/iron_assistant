"""Commitment lifecycle and authorization enforcement for Strategic Planning (Task 58)."""

from __future__ import annotations

import logging

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class PlanCommitment(BaseModel):
    commitment_id: str
    plan_id: str
    title: str
    description: str
    deadline: str | None = None
    resource_quota: dict[str, float] = Field(default_factory=dict)
    is_authorized: bool = False
    authorized_by: str | None = None
    status: str = "PROPOSED"  # PROPOSED, AUTHORIZED, REJECTED, FULFILLED


class PlanCommitmentManager:
    """Enforces authorization boundaries for external or internal strategic commitments."""

    def propose_commitment(
        self,
        plan_id: str,
        title: str,
        description: str,
        deadline: str | None = None,
        resource_quota: dict[str, float] | None = None,
    ) -> PlanCommitment:
        """Create a proposed commitment in PROPOSED state."""
        import uuid
        return PlanCommitment(
            commitment_id=f"cmt_{uuid.uuid4().hex[:8]}",
            plan_id=plan_id,
            title=title,
            description=description,
            deadline=deadline,
            resource_quota=resource_quota or {},
            is_authorized=False,
            authorized_by=None,
            status="PROPOSED",
        )

    def authorize_commitment(
        self,
        commitment: PlanCommitment,
        authorizer: str,
        authorizer_role: str,
    ) -> tuple[bool, str]:
        """Authorize a commitment if authorizer has executive or admin permissions."""
        allowed_roles = {"ADMIN", "EXECUTIVE", "SYSTEM_LEAD"}
        if authorizer_role.upper() not in allowed_roles:
            logger.warning(
                "Unauthorized attempt to seal commitment %s by %s (%s).",
                commitment.commitment_id,
                authorizer,
                authorizer_role,
            )
            return False, f"Role '{authorizer_role}' lacks authority to seal strategic commitments."

        commitment.is_authorized = True
        commitment.authorized_by = authorizer
        commitment.status = "AUTHORIZED"
        logger.info("Commitment %s authorized by %s.", commitment.commitment_id, authorizer)
        return True, "Commitment successfully authorized."


commitment_manager = PlanCommitmentManager()
