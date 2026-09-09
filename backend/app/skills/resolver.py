"""Deterministic and context-aware Skill Resolver matching user intent to skills."""

import logging
import re

from app.security.center import SecurityCenter, get_security_center
from app.security.permissions import Capability
from app.skills.registry import SkillRegistry
from app.skills.schemas import SkillManifest

logger = logging.getLogger("kairo.skills.resolver")

# Intent patterns mapped to candidate skill IDs in priority order
_INTENT_PATTERNS: list[tuple[re.Pattern, list[str]]] = [
    # 1. Computer Control
    (
        re.compile(r"\b(click|type|mouse|press key|move cursor|desktop control)\b", re.IGNORECASE),
        ["computer.assist"],
    ),
    # 2. Vision & Screen capture
    (
        re.compile(
            r"\b(screenshot|capture screen|screen image|inspect visual|look at screen)\b", re.IGNORECASE
        ),
        ["vision.analyze", "computer.assist"],
    ),
    # 3. Voice & Audio
    (re.compile(r"\b(voice|speak|listen|audio|transcribe|read aloud)\b", re.IGNORECASE), ["voice.assist"]),
    # 4. Automations & Workflows
    (
        re.compile(r"\b(workflow|automation|cron|trigger|schedule action|automate)\b", re.IGNORECASE),
        ["automation.manage"],
    ),
    # 5. GitHub & CI Investigation
    (
        re.compile(
            r"\b(ci|build failing|ci run|pull request|pr\b|github issue|github|workflow run failure)\b",
            re.IGNORECASE,
        ),
        ["github.analysis", "developer.repository"],
    ),
    # 6. Repository & Developer code inspection
    (
        re.compile(
            r"\b(git status|git diff|git log|codebase|repository|commit|read file|analyze code|run tests)\b",
            re.IGNORECASE,
        ),
        ["developer.repository", "github.analysis"],
    ),
    # 7. Document Analysis
    (
        re.compile(r"\b(document|pdf|docx|uploaded file|extract doc|summarize document)\b", re.IGNORECASE),
        ["documents.analyze", "knowledge.search"],
    ),
    # 8. Knowledge Fabric & Decisions
    (
        re.compile(
            r"\b(knowledge|knowledge fabric|knowledge graph|fabric memory|what changed|decision|architecture decision|timeline|what did we decide)\b",
            re.IGNORECASE,
        ),
        ["knowledge.search", "project.analysis"],
    ),
    # 9. Project Summary
    (
        re.compile(r"\b(project overview|project status|project activity|project summary)\b", re.IGNORECASE),
        ["project.analysis", "knowledge.search"],
    ),
    # 10. Web Research & Browsing
    (
        re.compile(r"\b(browse|navigate to|open website|scrape url)\b", re.IGNORECASE),
        ["browser.research", "research.web"],
    ),
    (
        re.compile(
            r"\b(research|web search|look up online|find documentation|search internet|latest news)\b",
            re.IGNORECASE,
        ),
        ["research.web"],
    ),
]


class SkillResolver:
    """Resolves user requests to the most appropriate, available, and authorized skill."""

    def __init__(
        self,
        registry: SkillRegistry,
        security_center: SecurityCenter | None = None,
    ) -> None:
        self.registry = registry
        self.security_center = security_center or get_security_center()

    def resolve(
        self,
        query: str,
        user_id: str = "default_user",
        explicit_skill_id: str | None = None,
        project_id: str | None = None,
        device_id: str | None = None,
        available_capabilities: set[str] | None = None,
    ) -> SkillManifest | None:
        """Resolve query to best candidate skill using deterministic priority signals."""
        # 1. Explicit Skill ID Match
        if explicit_skill_id:
            manifest = self.registry.get(explicit_skill_id, user_id=user_id)
            if manifest and manifest.enabled and self._is_candidate_authorized(manifest, user_id, available_capabilities):
                logger.info("Resolved explicitly requested skill: %s", manifest.id)
                return manifest
            logger.warning(
                "Explicitly requested skill '%s' is unavailable or unauthorized.", explicit_skill_id
            )
            return None

        clean_query = query.strip()
        if not clean_query:
            return None

        # 2. Match Deterministic Intent Patterns
        candidates: list[str] = []
        for pattern, skill_ids in _INTENT_PATTERNS:
            if pattern.search(clean_query):
                for s_id in skill_ids:
                    if s_id not in candidates:
                        candidates.append(s_id)

        # 3. Filter Candidates against Registry, Enable Status, and SecurityCenter Gates
        for candidate_id in candidates:
            manifest = self.registry.get(candidate_id, user_id=user_id)
            if not manifest or not manifest.enabled:
                continue

            # Context requirement checks
            if manifest.project_scoped and not project_id:
                continue
            if manifest.device_scoped and not device_id:
                continue

            if self._is_candidate_authorized(manifest, user_id, available_capabilities):
                logger.info(
                    "Deterministically resolved skill '%s' for query: '%s'", manifest.id, clean_query[:50]
                )
                return manifest

        # 4. Contextual Fallback: If project_id provided and query asks generic question
        if project_id and re.search(r"\b(status|summary|changes|progress)\b", clean_query, re.IGNORECASE):
            fallback_proj = self.registry.get("project.analysis", user_id=user_id)
            if fallback_proj and fallback_proj.enabled and self._is_candidate_authorized(fallback_proj, user_id, available_capabilities):
                return fallback_proj

        # 5. Default General Safe Fallback: Web Research
        fallback_res = self.registry.get("research.web", user_id=user_id)
        if fallback_res and fallback_res.enabled and self._is_candidate_authorized(fallback_res, user_id, available_capabilities):
            if re.search(r"\b(how|what|why|where|who|when|find|search)\b", clean_query, re.IGNORECASE):
                return fallback_res

        return None

    def _is_candidate_authorized(
        self,
        manifest: SkillManifest,
        user_id: str = "default_user",
        available_capabilities: set[str] | None = None,
    ) -> bool:
        """Check capability gates in SecurityCenter without performing full execution auth."""
        if self.security_center.is_emergency_stopped(user_id):
            return False

        if available_capabilities is not None:
            for cap_str in manifest.capabilities:
                if cap_str not in available_capabilities:
                    return False
            return True

        for cap_str in manifest.capabilities:
            try:
                cap_enum = Capability(cap_str)
                if cap_enum == Capability.COMPUTER_CONTROL and not self.security_center.settings.KAIRO_COMPUTER_ENABLED:
                    return False
                if cap_enum == Capability.BROWSER and not self.security_center.settings.KAIRO_BROWSER_ENABLED:
                    return False
                if cap_enum == Capability.AUTOMATION and not self.security_center.settings.KAIRO_AUTOMATION_ENABLED:
                    return False
                if cap_enum == Capability.DEVELOPER_TOOLS and not self.security_center.settings.KAIRO_DEVELOPER_ENABLED:
                    return False
                if cap_enum == Capability.VOICE and not self.security_center.settings.KAIRO_VOICE_ENABLED:
                    return False
            except ValueError:
                pass
        return True
