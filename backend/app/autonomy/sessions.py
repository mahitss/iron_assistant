"""Autonomous Session Management, Scope Boundaries, and Long-Horizon Context Compaction (Task 45)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
import uuid

logger = logging.getLogger("kairo.autonomy.sessions")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ScopeViolationError(Exception):
    """Raised when an autonomous action breaches explicit scope boundaries (Spec 144, 145)."""


class TenantIsolationError(Exception):
    """Raised when an operation attempts cross-user or cross-project access (Spec 4, 196)."""


@dataclass
class AutonomousScope:
    """Explicitly bounded scope for an autonomous run (Spec 144, 145)."""

    allowed_directories: List[str] = field(default_factory=list)
    allowed_domains: List[str] = field(default_factory=list)
    allowed_tools: List[str] = field(default_factory=list)
    max_subagents: int = 5
    max_steps: int = 50
    can_access_network: bool = True
    can_modify_filesystem: bool = True

    def validate_resource_in_scope(self, resource_path: str) -> bool:
        """Verify target file or path is inside allowed scope (Spec 145)."""
        if not self.allowed_directories:
            return True  # If no restrictive directories set, root bounds apply
        norm_res = resource_path.replace("\\", "/").lower()
        for allowed in self.allowed_directories:
            norm_allowed = allowed.replace("\\", "/").lower()
            if norm_res.startswith(norm_allowed):
                return True
        return False

    def validate_domain_in_scope(self, domain_name: str) -> bool:
        """Verify network target domain is within allowed scope (Spec 145)."""
        if not self.allowed_domains:
            return self.can_access_network
        norm_domain = domain_name.lower().strip()
        for allowed in self.allowed_domains:
            if norm_domain == allowed.lower() or norm_domain.endswith("." + allowed.lower()):
                return True
        return False


@dataclass
class AutonomousSession:
    """Durable long-horizon execution context preserving state across cycles (Spec 4, 125-128)."""

    session_id: str
    user_id: str
    project_id: str
    goal_id: str
    scope: AutonomousScope = field(default_factory=AutonomousScope)
    context_summary: str = ""
    critical_evidence_refs: List[str] = field(default_factory=list)
    security_decisions: List[Dict[str, Any]] = field(default_factory=list)
    approval_history: List[Dict[str, Any]] = field(default_factory=list)
    verification_records: List[Dict[str, Any]] = field(default_factory=list)
    failure_history: List[Dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def validate_tenant_access(self, requesting_user_id: str, requesting_project_id: str) -> None:
        """Enforce strict cross-user and cross-project isolation (Spec 4, 196)."""
        if self.user_id != requesting_user_id:
            logger.critical(
                "Cross-user isolation violation: User '%s' attempted to access run owned by '%s'",
                requesting_user_id,
                self.user_id,
            )
            raise TenantIsolationError(f"Access denied: Session belongs to user '{self.user_id}'.")
        if self.project_id != requesting_project_id:
            logger.critical(
                "Cross-project isolation violation: Project '%s' cannot access session of project '%s'",
                requesting_project_id,
                self.project_id,
            )
            raise TenantIsolationError(f"Access denied: Session belongs to project '{self.project_id}'.")

    def record_security_decision(self, action: str, allowed: bool, reason: str) -> None:
        self.security_decisions.append({
            "action": action,
            "allowed": allowed,
            "reason": reason,
            "timestamp": utc_now().isoformat(),
        })

    def record_approval(self, approval_id: str, action: str, approver: str, valid: bool) -> None:
        self.approval_history.append({
            "approval_id": approval_id,
            "action": action,
            "approver": approver,
            "valid": valid,
            "timestamp": utc_now().isoformat(),
        })

    def record_failure(self, step_id: str, error: str, category: str) -> None:
        self.failure_history.append({
            "step_id": step_id,
            "error": error,
            "category": category,
            "timestamp": utc_now().isoformat(),
        })

    def compact_context(self, intermediate_thoughts: List[str]) -> str:
        """Summarize execution context without losing critical evidence or security history (Spec 127, 128)."""
        # Compress transient thought logs into high-level digest
        thought_summary = f"Synthesized {len(intermediate_thoughts)} intermediate reasoning thoughts." if intermediate_thoughts else "No intermediate thoughts."
        
        # Preserved invariants (NEVER compressed away)
        preserved = (
            f"Security checks passed: {len(self.security_decisions)}; "
            f"Approvals: {len(self.approval_history)}; "
            f"Verifications: {len(self.verification_records)}; "
            f"Failures recorded: {len(self.failure_history)}; "
            f"Evidence items: {len(self.critical_evidence_refs)}."
        )
        self.context_summary = f"{thought_summary} | Invariants: {preserved}"
        self.updated_at = utc_now()
        return self.context_summary

    def reconstruct_cycle_context(self, active_plan_summary: str) -> Dict[str, Any]:
        """Reconstruct minimal, high-signal context for model cycle (Spec 126)."""
        return {
            "session_id": self.session_id,
            "goal_id": self.goal_id,
            "context_summary": self.context_summary,
            "active_plan": active_plan_summary,
            "security_decisions_count": len(self.security_decisions),
            "recent_failures": self.failure_history[-3:] if self.failure_history else [],
            "critical_evidence_refs": self.critical_evidence_refs,
        }
