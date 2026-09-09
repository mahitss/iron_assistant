"""Built-in production skills catalog defining Kairo's 11 canonical skills."""

from app.skills.registry import SkillRegistry
from app.skills.schemas import (
    ExecutionLimits,
    SkillCategory,
    SkillManifest,
    SkillRiskLevel,
)


def get_builtin_skill_manifests() -> list[SkillManifest]:
    """Return all 11 canonical Kairo built-in skill manifests."""
    return [
        # 1. Web Research
        SkillManifest(
            id="research.web",
            name="Web Research",
            description="Investigates web queries, retrieves top authoritative sources, and synthesizes structured findings with citations.",
            version="1.0.0",
            category=SkillCategory.RESEARCH,
            capabilities=["web_research"],
            required_tools=["web_search"],
            optional_tools=["web_fetch"],
            risk_level=SkillRiskLevel.READ_ONLY,
            permissions=["web.read"],
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search topic or research question"},
                    "max_results": {"type": "integer", "default": 5},
                },
                "required": ["query"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "summary": {"type": "string"},
                    "findings": {"type": "array"},
                    "sources": {"type": "array"},
                },
            },
            execution_limits=ExecutionLimits(max_steps=5, timeout_seconds=120, max_tool_calls=10),
            enabled=True,
            source="BUILTIN",
        ),
        # 2. Knowledge Search
        SkillManifest(
            id="knowledge.search",
            name="Knowledge Search",
            description="Performs multi-strategy hybrid retrieval over Kairo Knowledge Fabric connecting projects, decisions, and sources.",
            version="1.0.0",
            category=SkillCategory.KNOWLEDGE,
            capabilities=[],
            required_tools=[],
            optional_tools=[],
            risk_level=SkillRiskLevel.READ_ONLY,
            permissions=[],
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Knowledge search query"},
                    "project_id": {"type": "string", "description": "Optional project scoping identifier"},
                    "limit": {"type": "integer", "default": 10},
                },
                "required": ["query"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "summary": {"type": "string"},
                    "nodes": {"type": "array"},
                    "relationships": {"type": "array"},
                },
            },
            execution_limits=ExecutionLimits(max_steps=5, timeout_seconds=60, max_tool_calls=5),
            enabled=True,
            source="BUILTIN",
        ),
        # 3. Document Analysis
        SkillManifest(
            id="documents.analyze",
            name="Document Analysis",
            description="Parses user-provided documents, extracts semantic chunks, and answers inquiries grounded in verified document text.",
            version="1.0.0",
            category=SkillCategory.DOCUMENTS,
            capabilities=[],
            required_tools=[],
            optional_tools=[],
            risk_level=SkillRiskLevel.READ_ONLY,
            permissions=[],
            input_schema={
                "type": "object",
                "properties": {
                    "document_id": {"type": "string", "description": "Target document identifier"},
                    "query": {"type": "string", "description": "Specific question or analysis target"},
                },
                "required": ["query"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "summary": {"type": "string"},
                    "sections": {"type": "array"},
                    "evidence": {"type": "array"},
                },
            },
            execution_limits=ExecutionLimits(max_steps=5, timeout_seconds=90, max_tool_calls=10),
            enabled=True,
            source="BUILTIN",
        ),
        # 4. Developer Repository Analysis
        SkillManifest(
            id="developer.repository",
            name="Repository Analysis",
            description="Inspects local repository status, working tree diffs, commit logs, and static code metrics without executing arbitrary shell code.",
            version="1.0.0",
            category=SkillCategory.DEVELOPER,
            capabilities=["developer_tools"],
            required_tools=["git_status"],
            optional_tools=[
                "git_diff",
                "git_log",
                "code_search",
                "code_read_file",
                "code_analyze",
                "test_runner",
            ],
            risk_level=SkillRiskLevel.READ_ONLY,
            permissions=["repo.read"],
            input_schema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["status", "diff", "log", "analyze"],
                        "default": "status",
                    },
                    "path": {"type": "string", "description": "Relative file or directory path"},
                },
            },
            output_schema={
                "type": "object",
                "properties": {
                    "status": {"type": "string"},
                    "summary": {"type": "string"},
                    "findings": {"type": "array"},
                },
            },
            execution_limits=ExecutionLimits(max_steps=10, timeout_seconds=120, max_tool_calls=15),
            enabled=True,
            source="BUILTIN",
            project_scoped=False,
        ),
        # 5. GitHub Analysis
        SkillManifest(
            id="github.analysis",
            name="GitHub Investigation",
            description="Investigates GitHub repositories, issues, pull requests, and CI test runs to diagnose build failures and review changes.",
            version="1.0.0",
            category=SkillCategory.DEVELOPER,
            capabilities=["developer_tools"],
            required_tools=["github_get_repository"],
            optional_tools=[
                "github_list_issues",
                "github_get_issue",
                "github_list_pull_requests",
                "github_get_pull_request",
                "github_get_checks",
            ],
            risk_level=SkillRiskLevel.READ_ONLY,
            permissions=["github.read"],
            input_schema={
                "type": "object",
                "properties": {
                    "repository": {"type": "string", "description": "Repository identifier (owner/repo)"},
                    "pr_number": {"type": "integer", "description": "Optional pull request number"},
                    "issue_number": {"type": "integer", "description": "Optional issue number"},
                },
                "required": ["repository"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "summary": {"type": "string"},
                    "details": {"type": "object"},
                    "evidence": {"type": "array"},
                },
            },
            execution_limits=ExecutionLimits(max_steps=8, timeout_seconds=120, max_tool_calls=12),
            enabled=True,
            source="BUILTIN",
        ),
        # 6. Project Analysis
        SkillManifest(
            id="project.analysis",
            name="Project Analysis",
            description="Synthesizes cross-cutting project health, recent decisions, activity history, and linked repositories.",
            version="1.0.0",
            category=SkillCategory.PROJECTS,
            capabilities=[],
            required_tools=[],
            optional_tools=[],
            risk_level=SkillRiskLevel.READ_ONLY,
            permissions=["project.read"],
            input_schema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "description": "Active project identifier"},
                    "timeframe_days": {"type": "integer", "default": 7},
                },
                "required": ["project_id"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "string"},
                    "summary": {"type": "string"},
                    "decisions": {"type": "array"},
                },
            },
            execution_limits=ExecutionLimits(max_steps=5, timeout_seconds=60, max_tool_calls=5),
            enabled=True,
            source="BUILTIN",
            project_scoped=True,
        ),
        # 7. Automation Management
        SkillManifest(
            id="automation.manage",
            name="Automation Management",
            description="Manages automated workflows, scheduled triggers, and routine task configurations with explicit write authorization.",
            version="1.0.0",
            category=SkillCategory.AUTOMATION,
            capabilities=["automation"],
            required_tools=[],
            optional_tools=[],
            risk_level=SkillRiskLevel.HIGH,
            permissions=["automation.write"],
            input_schema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["list", "inspect", "create", "update", "pause", "resume"],
                        "default": "list",
                    },
                    "workflow_id": {"type": "string"},
                },
                "required": ["action"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "status": {"type": "string"},
                    "workflow": {"type": "object"},
                },
            },
            execution_limits=ExecutionLimits(max_steps=5, timeout_seconds=60, max_tool_calls=5),
            enabled=True,
            source="BUILTIN",
        ),
        # 8. Browser Research
        SkillManifest(
            id="browser.research",
            name="Browser Research",
            description="Controls sandboxed browser sessions for web navigation, visual inspection, and protected DOM data extraction.",
            version="1.0.0",
            category=SkillCategory.BROWSER,
            capabilities=["browser"],
            required_tools=["browser_navigate"],
            optional_tools=["browser_inspect", "browser_screenshot", "browser_click", "browser_fill"],
            risk_level=SkillRiskLevel.LOW,
            permissions=["browser.navigate"],
            input_schema={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Target web page URL"},
                    "action": {
                        "type": "string",
                        "enum": ["navigate", "inspect", "screenshot"],
                        "default": "navigate",
                    },
                },
                "required": ["url"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "status": {"type": "string"},
                    "title": {"type": "string"},
                    "content": {"type": "string"},
                },
            },
            execution_limits=ExecutionLimits(max_steps=6, timeout_seconds=120, max_tool_calls=10),
            enabled=True,
            source="BUILTIN",
        ),
        # 9. Voice Interaction
        SkillManifest(
            id="voice.assist",
            name="Voice Interaction",
            description="Coordinates bidirectional speech audio synthesis and transcription without background silent recording.",
            version="1.0.0",
            category=SkillCategory.VOICE,
            capabilities=["voice"],
            required_tools=[],
            optional_tools=[],
            risk_level=SkillRiskLevel.LOW,
            permissions=["audio.read"],
            input_schema={
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["transcribe", "speak"], "default": "speak"},
                    "text": {"type": "string", "description": "Text to synthesize into speech"},
                },
                "required": ["action"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "status": {"type": "string"},
                    "audio_status": {"type": "string"},
                },
            },
            execution_limits=ExecutionLimits(max_steps=3, timeout_seconds=30, max_tool_calls=3),
            enabled=True,
            source="BUILTIN",
        ),
        # 10. Vision Analysis
        SkillManifest(
            id="vision.analyze",
            name="Vision Analysis",
            description="Analyzes user-provided images or explicit authorized desktop screenshots with optical character recognition.",
            version="1.0.0",
            category=SkillCategory.VISION,
            capabilities=["vision"],
            required_tools=[],
            optional_tools=["computer_screenshot"],
            risk_level=SkillRiskLevel.LOW,
            permissions=["screen.read"],
            input_schema={
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "Visual analysis inquiry"},
                    "capture_screen": {"type": "boolean", "default": False},
                },
                "required": ["prompt"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "description": {"type": "string"},
                    "findings": {"type": "array"},
                },
            },
            execution_limits=ExecutionLimits(max_steps=4, timeout_seconds=60, max_tool_calls=5),
            enabled=True,
            source="BUILTIN",
        ),
        # 11. Computer Assistance
        SkillManifest(
            id="computer.assist",
            name="Computer Assistance",
            description="Executes verified mouse clicks and keystrokes on the user's desktop via Local Companion under strict human-in-the-loop approval.",
            version="1.0.0",
            category=SkillCategory.COMPUTER,
            capabilities=["computer_control"],
            required_tools=["computer_screenshot"],
            optional_tools=[
                "computer_click",
                "computer_type",
                "computer_press_key",
                "computer_mouse_move",
                "computer_mouse_scroll",
            ],
            risk_level=SkillRiskLevel.HIGH,
            permissions=["desktop.input"],
            input_schema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["screenshot", "click", "type"],
                        "default": "screenshot",
                    },
                    "x": {"type": "integer"},
                    "y": {"type": "integer"},
                    "text": {"type": "string"},
                },
                "required": ["action"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "status": {"type": "string"},
                    "action_performed": {"type": "string"},
                },
            },
            execution_limits=ExecutionLimits(max_steps=5, timeout_seconds=60, max_tool_calls=5),
            enabled=False,
            source="BUILTIN",
            device_scoped=True,
        ),
    ]


def populate_default_skills(registry: SkillRegistry) -> None:
    """Register all canonical built-in skills into the given SkillRegistry."""
    for manifest in get_builtin_skill_manifests():
        registry.register(manifest, allow_override=True)


create_default_skills = get_builtin_skill_manifests
