"""REST API endpoints for Kairo Governance and Policy Engine (Task 36, Spec 150, 151).

Provides:
- Policy evaluation & simulation endpoints for client/runtime subsystems.
- Secure administrative governance management with strict role checks and audit logging.
"""

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status

from app.policy.engine import policy_engine
from app.policy.schemas import (
    PolicyCreateRequest,
    PolicyDecision,
    PolicyEvaluateRequest,
    PolicyRollbackRequest,
    PolicyRule,
    PolicySimulationRequest,
    PolicySimulationResponse,
    PolicyStatusResponse,
    PolicyUpdateRequest,
)

logger = logging.getLogger("kairo.policy.router")

# Client / Runtime Policy Router: /api/v1/policy
router = APIRouter(prefix="/policy", tags=["policy"])

# Protected Admin Policy Router: /api/v1/admin
admin_router = APIRouter(prefix="/admin", tags=["policy-admin"])


# ==========================================
# Security Dependencies
# ==========================================

def get_current_user_id(x_user_id: Annotated[str | None, Header()] = None) -> str:
    """Extract authenticated user ID from request header."""
    return x_user_id.strip() if x_user_id and x_user_id.strip() else "default_user"


def require_policy_admin(
    x_user_role: Annotated[str | None, Header()] = None,
    x_user_id: Annotated[str | None, Header()] = None,
    x_caller_type: Annotated[str | None, Header()] = None,
) -> str:
    """Enforce strict administrative authorization for policy mutations (Sections 83, 84, 151, 152).

    Prevents AI models/agents and unprivileged users from mutating governance policies.
    """
    caller_type = (x_caller_type or "").lower()
    if caller_type in ("agent", "model", "llm", "autonomous_task"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="AI agents and models are strictly prohibited from mutating governance policies",
        )

    role = (x_user_role or "").lower()
    if role not in ("admin", "superadmin", "security_admin", "system"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrative authorization required to access or modify governance policies",
        )

    return x_user_id or "system_admin"


# ==========================================
# Client & Runtime Subsystem Endpoints
# ==========================================

@router.post("/evaluate", response_model=PolicyDecision, status_code=status.HTTP_200_OK)
async def evaluate_policy(request: PolicyEvaluateRequest) -> PolicyDecision:
    """Evaluate a requested action context against all active governance rules."""
    try:
        return await policy_engine.evaluate(request.context, simulate=request.simulate)
    except Exception as e:
        logger.error(f"Error evaluating policy: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/simulate", response_model=PolicySimulationResponse, status_code=status.HTTP_200_OK)
async def simulate_policy(request: PolicySimulationRequest) -> PolicySimulationResponse:
    """Simulate a proposed action against current policies or a hypothetical candidate policy."""
    try:
        return await policy_engine.simulate(request)
    except Exception as e:
        logger.error(f"Error simulating policy: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/decision/{evaluation_id}", response_model=dict[str, Any], status_code=status.HTTP_200_OK)
async def get_decision_provenance(evaluation_id: str) -> dict[str, Any]:
    """Retrieve decision provenance trace and matched policies for an evaluation UUID."""
    record = policy_engine.provenance.get_evaluation(evaluation_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Evaluation record '{evaluation_id}' not found")
    return record


@router.get("/status", response_model=PolicyStatusResponse, status_code=status.HTTP_200_OK)
async def get_policy_status() -> PolicyStatusResponse:
    """Return overall health, counts, and active environment restrictions."""
    policies = policy_engine.registry.list_policies(include_disabled=True)
    from app.security.emergency_stop import get_emergency_stop_service
    es_active = get_emergency_stop_service().is_emergency_stop_active()

    return PolicyStatusResponse(
        total_policies=len(policies),
        active_policies=len([p for p in policies if p.enabled and not p.shadow_mode]),
        shadow_policies=len([p for p in policies if p.shadow_mode]),
        system_policies=len([p for p in policies if p.is_system]),
        emergency_stop_active=es_active,
        safe_mode_active=policy_engine.environments.is_safe_mode,
        change_freeze_environments=policy_engine.environments.get_frozen_environments(),
        incident_mode=policy_engine.environments.is_incident_mode,
        cached_decisions_count=policy_engine.registry.cached_count,
    )


# ==========================================
# Administrative Endpoints (Spec 151)
# ==========================================

@admin_router.get("/policies", response_model=list[PolicyRule], status_code=status.HTTP_200_OK)
async def list_policies(
    include_disabled: bool = Query(default=True),
    admin_id: str = Depends(require_policy_admin),
) -> list[PolicyRule]:
    """List all registered governance policies (Admin only)."""
    return policy_engine.registry.list_policies(include_disabled=include_disabled)


@admin_router.post("/policies", response_model=PolicyRule, status_code=status.HTTP_201_CREATED)
async def create_policy(
    request: PolicyCreateRequest,
    admin_id: str = Depends(require_policy_admin),
) -> PolicyRule:
    """Create and activate a new governance policy (Admin only)."""
    try:
        return policy_engine.registry.create_policy(request, creator=admin_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@admin_router.put("/policies/{policy_id}", response_model=PolicyRule, status_code=status.HTTP_200_OK)
async def update_policy(
    policy_id: str,
    request: PolicyUpdateRequest,
    admin_id: str = Depends(require_policy_admin),
) -> PolicyRule:
    """Update a policy by creating a new incremented version (Admin only)."""
    try:
        return policy_engine.registry.update_policy(policy_id, request, updater=admin_id)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Policy '{policy_id}' not found")
    except PermissionError as pe:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(pe))
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))


@admin_router.post("/policies/{policy_id}/activate", response_model=PolicyRule, status_code=status.HTTP_200_OK)
async def activate_policy(
    policy_id: str,
    admin_id: str = Depends(require_policy_admin),
) -> PolicyRule:
    """Activate an enabled policy (Admin only)."""
    try:
        return policy_engine.registry.update_policy(policy_id, PolicyUpdateRequest(enabled=True), updater=admin_id)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Policy '{policy_id}' not found")


@admin_router.post("/policies/{policy_id}/disable", response_model=PolicyRule, status_code=status.HTTP_200_OK)
async def disable_policy(
    policy_id: str,
    admin_id: str = Depends(require_policy_admin),
) -> PolicyRule:
    """Disable a policy (Admin only)."""
    try:
        return policy_engine.registry.update_policy(policy_id, PolicyUpdateRequest(enabled=False), updater=admin_id)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Policy '{policy_id}' not found")
    except PermissionError as pe:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(pe))


@admin_router.post("/policies/{policy_id}/rollback", response_model=PolicyRule, status_code=status.HTTP_200_OK)
async def rollback_policy(
    policy_id: str,
    request: PolicyRollbackRequest,
    admin_id: str = Depends(require_policy_admin),
) -> PolicyRule:
    """Roll back policy to a prior version (Admin only)."""
    try:
        return policy_engine.registry.rollback_policy(policy_id, request, operator=admin_id)
    except KeyError as ke:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ke))


@admin_router.post("/freeze", status_code=status.HTTP_200_OK)
async def set_change_freeze(
    environment: str = Query(..., description="Target environment"),
    active: bool = Query(..., description="Activate or deactivate freeze"),
    reason: str = Query(default=""),
    admin_id: str = Depends(require_policy_admin),
) -> dict[str, Any]:
    """Toggle change freeze on an environment (Admin only)."""
    policy_engine.environments.set_change_freeze(environment, active, reason=reason, authorized_by=admin_id)
    policy_engine.registry.invalidate_cache()
    return {"environment": environment, "change_freeze": active, "reason": reason}


@admin_router.post("/safemode", status_code=status.HTTP_200_OK)
async def toggle_safe_mode(
    enabled: bool = Query(...),
    admin_id: str = Depends(require_policy_admin),
) -> dict[str, Any]:
    """Toggle system safe mode (Admin only)."""
    policy_engine.environments.set_safe_mode(enabled)
    policy_engine.registry.invalidate_cache()
    return {"safe_mode": enabled, "updated_by": admin_id}
