"""Thread-safe, validated Skill Registry managing skill manifests, dependencies, and health."""

import logging
import re

from app.skills.schemas import (
    SkillCategory,
    SkillHealthStatus,
    SkillManifest,
)
from app.tools.registry import ToolRegistry

logger = logging.getLogger("kairo.skills.registry")

_ID_PATTERN = re.compile(r"^[a-z0-9_\-]+\.[a-z0-9_\-]+$")
_VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")


class SkillRegistryError(ValueError):
    """Base exception for skill registry operations."""


class DuplicateSkillError(SkillRegistryError):
    """Raised when attempting to register a skill with an existing ID."""


class InvalidSkillManifestError(SkillRegistryError):
    """Raised when a skill manifest fails canonical structure validation."""


class CircularDependencyError(SkillRegistryError):
    """Raised when skills form a circular composition dependency."""


class SkillRegistry:
    """Registry maintaining active production skills and resolving operational health."""

    def __init__(self, tool_registry: ToolRegistry | None = None) -> None:
        self._skills: dict[str, SkillManifest] = {}
        self._tool_registry = tool_registry
        # User-specific enable/disable overrides: {user_id: {skill_id: bool}}
        self._user_toggles: dict[str, dict[str, bool]] = {}

    def set_tool_registry(self, tool_registry: ToolRegistry) -> None:
        """Assign or update tool registry reference for health resolution."""
        self._tool_registry = tool_registry

    def register(self, manifest: SkillManifest, allow_override: bool = False) -> None:
        """Register a trusted skill definition, validating ID, version, and dependencies."""
        # 0. Reject model-generated or untrusted skill manifests (Section 5 & 78)
        src = str(manifest.source).upper()
        if "MODEL" in src or "UNTRUSTED" in src:
            raise PermissionError(
                f"Model-generated or untrusted skill '{manifest.id}' cannot be registered. "
                "Only trusted application code may register skills."
            )

        # 1. Validate ID format
        if not _ID_PATTERN.match(manifest.id):
            raise InvalidSkillManifestError(
                f"Skill ID '{manifest.id}' is invalid. Must be namespaced format (e.g. 'category.action')."
            )

        # 2. Validate SemVer format
        if not _VERSION_PATTERN.match(manifest.version):
            raise InvalidSkillManifestError(
                f"Skill '{manifest.id}' version '{manifest.version}' is invalid. Must be MAJOR.MINOR.PATCH."
            )

        # 3. Duplicate check
        if manifest.id in self._skills and not allow_override:
            raise DuplicateSkillError(f"A skill with ID '{manifest.id}' is already registered.")

        # 4. Dependency cycle check
        temp_skills = dict(self._skills)
        temp_skills[manifest.id] = manifest
        self._detect_cycles(temp_skills)

        self._skills[manifest.id] = manifest
        logger.info(
            "Registered skill '%s' v%s (category=%s)", manifest.id, manifest.version, manifest.category.value
        )

    def get(self, skill_id: str, user_id: str | None = None) -> SkillManifest | None:
        """Retrieve skill manifest, reflecting user-specific enable toggle if present."""
        manifest = self._skills.get(skill_id)
        if not manifest:
            return None

        if user_id and user_id in self._user_toggles:
            user_override = self._user_toggles[user_id].get(skill_id)
            if user_override is not None:
                # Return copy with user toggle applied
                copy_dict = manifest.model_dump()
                copy_dict["enabled"] = user_override
                return SkillManifest.model_validate(copy_dict)

        return manifest

    def list_skills(
        self,
        category: SkillCategory | None = None,
        enabled_only: bool = False,
        user_id: str | None = None,
    ) -> list[SkillManifest]:
        """List registered skills filtered by category and enabled status."""
        results: list[SkillManifest] = []
        for s_id in sorted(self._skills.keys()):
            manifest = self.get(s_id, user_id=user_id)
            if not manifest:
                continue
            if category and manifest.category != category:
                continue
            if enabled_only and not manifest.enabled:
                continue
            results.append(manifest)
        return results

    def toggle_skill(self, skill_id: str, enabled: bool, user_id: str | None = None) -> bool:
        """Toggle enabled state globally or for a specific user."""
        if skill_id not in self._skills:
            return False

        if user_id:
            if user_id not in self._user_toggles:
                self._user_toggles[user_id] = {}
            self._user_toggles[user_id][skill_id] = enabled
        else:
            self._skills[skill_id].enabled = enabled

        logger.info("Skill '%s' enabled set to %s (user=%s)", skill_id, enabled, user_id or "global")
        return True

    def set_enabled(self, skill_id: str, enabled: bool, user_id: str | None = None) -> SkillManifest:
        """Set skill enabled state and return the updated manifest."""
        if skill_id not in self._skills:
            raise ValueError(f"Skill '{skill_id}' is not registered.")
        self.toggle_skill(skill_id, enabled, user_id=user_id)
        retrieved = self.get(skill_id, user_id=user_id)
        if not retrieved:
            raise ValueError(f"Skill '{skill_id}' not found after update.")
        return retrieved

    def is_enabled(self, skill_id: str, user_id: str | None = None) -> bool:
        """Check whether a skill is enabled."""
        manifest = self.get(skill_id, user_id=user_id)
        return manifest.enabled if manifest else False

    def get_health(
        self, skill_id: str, available_tools: set[str] | None = None
    ) -> SkillHealthStatus:
        """Evaluate and return operational health status."""
        manifest = self._skills.get(skill_id)
        if not manifest or not manifest.enabled:
            return SkillHealthStatus.UNAVAILABLE

        if available_tools is not None:
            missing_req = [t for t in manifest.required_tools if t not in available_tools]
            if missing_req:
                return SkillHealthStatus.DEGRADED if not manifest.required_tools else SkillHealthStatus.UNAVAILABLE
            return SkillHealthStatus.HEALTHY

        status, _ = self.resolve_health(skill_id)
        return status

    def resolve_health(self, skill_id: str) -> tuple[SkillHealthStatus, str | None]:
        """Evaluate operational health based on tool availability and dependency readiness."""
        manifest = self._skills.get(skill_id)
        if not manifest:
            return SkillHealthStatus.UNAVAILABLE, f"Skill '{skill_id}' is not registered."

        if not manifest.enabled:
            return SkillHealthStatus.UNAVAILABLE, "Skill is disabled."

        # Check required tools in ToolRegistry
        if self._tool_registry:
            missing_required = [
                tool for tool in manifest.required_tools if not self._tool_registry.has_tool(tool)
            ]
            if missing_required:
                return (
                    SkillHealthStatus.UNAVAILABLE,
                    f"Required tools missing from registry: {', '.join(missing_required)}",
                )

            missing_optional = [
                tool for tool in manifest.optional_tools if not self._tool_registry.has_tool(tool)
            ]
            if missing_optional:
                return (
                    SkillHealthStatus.DEGRADED,
                    f"Optional tools unavailable: {', '.join(missing_optional)}",
                )

        # Check skill dependencies
        for dep_id in manifest.depends_on:
            dep_manifest = self._skills.get(dep_id)
            if not dep_manifest or not dep_manifest.enabled:
                return (
                    SkillHealthStatus.DEGRADED,
                    f"Dependent skill '{dep_id}' is unavailable or disabled.",
                )

        return SkillHealthStatus.HEALTHY, "All tools and dependencies are operational."

    def _detect_cycles(self, skills_map: dict[str, SkillManifest]) -> None:
        """Check for circular dependencies using depth-first cycle detection."""
        visited: set[str] = set()
        rec_stack: set[str] = set()

        def dfs(node_id: str) -> None:
            visited.add(node_id)
            rec_stack.add(node_id)

            manifest = skills_map.get(node_id)
            if manifest:
                dep_targets = list(dict.fromkeys(manifest.depends_on + getattr(manifest, "dependencies", [])))
                for neighbor in dep_targets:
                    if neighbor not in visited:
                        dfs(neighbor)
                    elif neighbor in rec_stack:
                        raise CircularDependencyError(
                            f"Circular dependency detected involving skill '{neighbor}' and '{node_id}'."
                        )

            rec_stack.remove(node_id)

        for s_id in skills_map:
            if s_id not in visited:
                dfs(s_id)


_global_skill_registry: SkillRegistry | None = None


def get_skill_registry() -> SkillRegistry:
    """Return canonical global SkillRegistry singleton."""
    global _global_skill_registry
    if _global_skill_registry is None:
        _global_skill_registry = SkillRegistry()
    return _global_skill_registry
