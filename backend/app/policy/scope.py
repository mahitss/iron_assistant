"""Scope hierarchy and authorization boundaries for Kairo Policy Engine (Task 36).

Ensures specific policies only restrict, never expand prohibited capabilities.
Enforces strict boundaries against cross-user and cross-project access.
"""

from typing import Any

from app.policy.schemas import PolicyContext, PolicyDecisionType, PolicyRule, PolicyScope


class ScopeHierarchyEvaluator:
    """Manages hierarchical scope matching and scope expansion validation."""

    SCOPE_ORDER: dict[PolicyScope, int] = {
        PolicyScope.GLOBAL: 0,
        PolicyScope.USER: 1,
        PolicyScope.PROJECT: 2,
        PolicyScope.ENVIRONMENT: 3,
        PolicyScope.DEVICE: 4,
        PolicyScope.SESSION: 4,
        PolicyScope.TASK: 5,
        PolicyScope.TOOL: 6,
        PolicyScope.SKILL: 6,
        PolicyScope.DATA_TYPE: 6,
    }

    @classmethod
    def matches_scope(cls, rule: PolicyRule, context: PolicyContext) -> bool:
        """Determine if a rule applies to the given execution context scope."""
        scope = rule.scope
        target_id = rule.target_scope_id

        if scope == PolicyScope.GLOBAL:
            return True

        if scope == PolicyScope.USER:
            user_id = (context.user or {}).get("id") or (context.user or {}).get("user_id")
            return target_id is None or (user_id is not None and str(user_id) == str(target_id))

        if scope == PolicyScope.PROJECT:
            project_id = (context.project or {}).get("id") or (context.project or {}).get("project_id")
            return target_id is None or (project_id is not None and str(project_id) == str(target_id))

        if scope == PolicyScope.ENVIRONMENT:
            env = context.environment
            return target_id is None or (env is not None and env.lower() == str(target_id).lower())

        if scope == PolicyScope.DEVICE:
            device_id = (context.device or {}).get("id") or (context.device or {}).get("device_id")
            return target_id is None or (device_id is not None and str(device_id) == str(target_id))

        if scope == PolicyScope.SESSION:
            session_id = (context.session or {}).get("id") or (context.session or {}).get("session_id")
            return target_id is None or (session_id is not None and str(session_id) == str(target_id))

        if scope == PolicyScope.TASK:
            task_id = (context.task or {}).get("id") or (context.task or {}).get("task_id")
            task_type = (context.task or {}).get("type") or (context.task or {}).get("task_type")
            return target_id is None or target_id in (task_id, task_type)

        if scope == PolicyScope.TOOL:
            tool_name = ""
            if isinstance(context.tool, dict):
                tool_name = context.tool.get("name", "")
            elif isinstance(context.tool, str):
                tool_name = context.tool
            return target_id is None or (tool_name and tool_name.lower() == str(target_id).lower())

        if scope == PolicyScope.SKILL:
            skill_name = ""
            if isinstance(context.skill, dict):
                skill_name = context.skill.get("name", "")
            elif isinstance(context.skill, str):
                skill_name = context.skill
            return target_id is None or (skill_name and skill_name.lower() == str(target_id).lower())

        if scope == PolicyScope.DATA_TYPE:
            classification = (context.data_scope or {}).get("classification")
            return target_id is None or (classification and str(classification).upper() == str(target_id).upper())

        return False

    @staticmethod
    def validate_cross_boundary_access(context: PolicyContext) -> tuple[bool, str | None]:
        """Verify cross-user and cross-project boundaries (Sections 74, 75).

        Default: DENY cross-project or cross-user access unless explicitly authorized.
        """
        user = context.user or {}
        user_id = user.get("id") or user.get("user_id")
        user_role = user.get("role", "user")

        target_dict = context.target if isinstance(context.target, dict) else {}

        # Cross-user check
        target_owner = target_dict.get("owner_id") or target_dict.get("user_id")
        if target_owner and user_id and str(target_owner) != str(user_id):
            if user_role not in ("admin", "superadmin", "system"):
                return False, f"Cross-user access denied: user '{user_id}' cannot access resource owned by '{target_owner}'"

        # Cross-project check
        user_project = (context.project or {}).get("id") or (context.project or {}).get("project_id")
        target_project = target_dict.get("project_id")
        if target_project and user_project and str(target_project) != str(user_project):
            allowed_projects = (context.project or {}).get("allowed_projects", [])
            if str(target_project) not in [str(p) for p in allowed_projects] and user_role not in ("admin", "system"):
                return False, f"Cross-project access denied: project '{user_project}' cannot access '{target_project}'"

        return True, None

    @staticmethod
    def validate_task_scope_expansion(context: PolicyContext) -> tuple[bool, str | None]:
        """Check if an autonomous task is attempting to modify resources outside its authorized scope."""
        task = context.task
        if not task:
            return True, None

        authorized_scope = task.get("authorized_scope")
        if not authorized_scope:
            return True, None  # No explicit scope boundary configured on task

        target = context.target
        target_resource = ""
        if isinstance(target, dict):
            target_resource = target.get("path") or target.get("repository") or target.get("id") or ""
        elif isinstance(target, str):
            target_resource = target

        allowed_resources = authorized_scope.get("allowed_resources") or authorized_scope.get("repositories", [])
        if allowed_resources and target_resource:
            if not any(target_resource.startswith(r) or r in target_resource for r in allowed_resources):
                return False, f"Scope expansion violation: Task '{task.get('id')}' is not authorized to touch '{target_resource}'"

        # Environment boundary check on task
        allowed_environments = authorized_scope.get("environments", [])
        if allowed_environments and context.environment:
            if context.environment.lower() not in [e.lower() for e in allowed_environments]:
                return False, f"Task environment violation: Task '{task.get('id')}' cannot execute in '{context.environment}'"

        return True, None
