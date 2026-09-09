"""Agent Registry maintaining definitions, allowed tools, and capability taxonomy for specialists."""

import logging

from app.agents.schemas import AgentDefinition
from app.agents.state import AgentType
from app.models.registry import ModelCapability

logger = logging.getLogger("kairo.agents.registry")


class AgentRegistryError(Exception):
    """Base exception for agent registry errors."""


class UnknownAgentError(AgentRegistryError):
    """Raised when an un-registered agent role is requested."""


class DuplicateAgentError(AgentRegistryError):
    """Raised when attempting to register an agent under an existing type."""


class AgentRegistry:
    """Registry maintaining authorized specialist and supervisor agent specifications."""

    def __init__(self) -> None:
        self._definitions: dict[str, AgentDefinition] = {}

    def register(self, definition: AgentDefinition) -> None:
        """Register an agent definition, preventing dynamic re-definition."""
        key = str(definition.agent_type).upper()
        if key in self._definitions:
            raise DuplicateAgentError(f"Agent '{key}' is already registered.")
        if not definition.role:
            definition.role = key
        self._definitions[key] = definition

    def unregister(self, agent_type: AgentType | str) -> bool:
        """Unregister an agent definition."""
        key = str(agent_type).upper()
        if key in self._definitions:
            del self._definitions[key]
            return True
        return False

    def get(self, agent_type: AgentType | str) -> AgentDefinition:
        """Retrieve registered agent definition or raise UnknownAgentError."""
        key = str(agent_type).upper()
        defn = self._definitions.get(key)
        if not defn:
            raise UnknownAgentError(
                f"Agent type '{key}' is not registered. Available: {list(self._definitions.keys())}"
            )
        return defn

    def has_agent(self, agent_type: AgentType | str) -> bool:
        """Check if an agent type is registered."""
        return str(agent_type).upper() in self._definitions

    def list_agents(self) -> list[AgentDefinition]:
        """List all registered agent definitions."""
        return list(self._definitions.values())

    def discover(
        self,
        role: str | None = None,
        capability: str | None = None,
    ) -> list[AgentDefinition]:
        """Discover agents matching optional role or capability filters."""
        results = []
        for defn in self._definitions.values():
            if role and defn.role.upper() != role.upper() and str(defn.agent_type).upper() != role.upper():
                continue
            if capability and capability not in defn.capabilities and capability not in defn.allowed_tools:
                continue
            results.append(defn)
        return results

    def health_check(self, agent_type: AgentType | str) -> str:
        """Retrieve health status of registered agent."""
        defn = self.get(agent_type)
        return defn.health_status

    def capability_lookup(self, agent_type: AgentType | str) -> list[str]:
        """Lookup capabilities and allowed tools of agent."""
        defn = self.get(agent_type)
        return list(set(defn.capabilities + defn.allowed_tools))

    def version_lookup(self, agent_type: AgentType | str) -> str:
        """Lookup version of agent."""
        defn = self.get(agent_type)
        return defn.version


def create_default_agent_registry() -> AgentRegistry:
    """Instantiate and configure standard Kairo supervisor and specialist agents."""
    registry = AgentRegistry()

    # 1. SUPERVISOR
    registry.register(
        AgentDefinition(
            name="Supervisor",
            agent_type=AgentType.SUPERVISOR,
            description="Decomposes complex requests, delegates to specialists, and synthesizes final answer.",
            allowed_tools=[],
            model_capability=ModelCapability.REASONING.value,
            max_execution_time_seconds=300,
            max_tool_calls=0,
            version="1.0.0",
            capabilities=["decompose", "delegate", "synthesize", "resolve"],
        )
    )

    # 2. RESEARCHER
    registry.register(
        AgentDefinition(
            name="Researcher",
            agent_type=AgentType.RESEARCHER,
            description="Searches public web, inspects documentation, and gathers source citations.",
            allowed_tools=["web_search", "web_fetch"],
            model_capability=ModelCapability.FAST.value,
            max_execution_time_seconds=120,
            max_tool_calls=10,
            version="1.0.0",
            capabilities=["research", "citation_gathering", "fact_extraction"],
        )
    )

    # 3. DEVELOPER / CODER
    registry.register(
        AgentDefinition(
            name="Developer",
            agent_type=AgentType.DEVELOPER,
            description="Inspects repositories, Git history/status/diffs, code search, and runs approved tests.",
            allowed_tools=[
                "git_status",
                "git_branches",
                "git_log",
                "git_diff",
                "code_search",
                "code_read_file",
                "code_analyze",
                "github_get_repository",
                "github_get_issue",
                "github_get_pull_request",
                "github_get_pr_diff",
                "github_get_checks",
                "test_runner",
            ],
            model_capability=ModelCapability.CODING.value,
            max_execution_time_seconds=180,
            max_tool_calls=15,
            version="1.0.0",
            capabilities=["code_generation", "code_patching", "git_operations"],
        )
    )

    # 4. ANALYST
    registry.register(
        AgentDefinition(
            name="Analyst",
            agent_type=AgentType.ANALYST,
            description="Compares structured evidence, detects contradictions, and synthesizes conclusions.",
            allowed_tools=[],  # Pure cognitive synthesis; no external tools
            model_capability=ModelCapability.REASONING.value,
            max_execution_time_seconds=120,
            max_tool_calls=0,
            version="1.0.0",
            capabilities=["evidence_analysis", "contradiction_detection", "logic_evaluation"],
        )
    )

    # 5. BROWSER
    registry.register(
        AgentDefinition(
            name="Browser",
            agent_type=AgentType.BROWSER,
            description="Performs controlled browser page inspection and visual verification under user consent.",
            allowed_tools=[
                "browser_open",
                "browser_navigate",
                "browser_inspect",
                "browser_screenshot",
                "browser_click",
                "browser_fill",
            ],
            model_capability=ModelCapability.GENERAL.value,
            max_execution_time_seconds=180,
            max_tool_calls=10,
            version="1.0.0",
            capabilities=["browser_navigation", "visual_inspection", "dom_interaction"],
        )
    )

    # 6. TESTER
    registry.register(
        AgentDefinition(
            name="Tester",
            agent_type="TESTER",
            description="Generates test suites, executes unit and integration tests, and validates assertions.",
            allowed_tools=["test_runner", "code_read_file"],
            model_capability=ModelCapability.CODING.value,
            max_execution_time_seconds=180,
            max_tool_calls=15,
            version="1.0.0",
            capabilities=["test_execution", "test_generation", "regression_testing"],
        )
    )

    # 7. VERIFIER
    registry.register(
        AgentDefinition(
            name="Verifier",
            agent_type="VERIFIER",
            description="Performs independent verification of claims, evidence, and code against success criteria.",
            allowed_tools=["code_read_file", "test_runner"],
            model_capability=ModelCapability.REASONING.value,
            max_execution_time_seconds=150,
            max_tool_calls=10,
            version="1.0.0",
            capabilities=["independent_verification", "contract_validation", "evidence_audit"],
        )
    )

    # 8. SECURITY_ANALYST
    registry.register(
        AgentDefinition(
            name="Security Analyst",
            agent_type="SECURITY_ANALYST",
            description="Inspects code, dependencies, and configuration for vulnerabilities and secret leakage.",
            allowed_tools=["code_read_file", "code_search"],
            model_capability=ModelCapability.REASONING.value,
            max_execution_time_seconds=180,
            max_tool_calls=15,
            version="1.0.0",
            capabilities=["vulnerability_scanning", "secret_detection", "security_review"],
        )
    )

    # 9. REVIEWER
    registry.register(
        AgentDefinition(
            name="Reviewer",
            agent_type="REVIEWER",
            description="Provides blind, independent code and architecture reviews without author bias.",
            allowed_tools=["code_read_file"],
            model_capability=ModelCapability.REASONING.value,
            max_execution_time_seconds=180,
            max_tool_calls=10,
            version="1.0.0",
            capabilities=["blind_review", "code_review", "compliance_audit"],
        )
    )

    # 10. PLANNER
    registry.register(
        AgentDefinition(
            name="Planner",
            agent_type="PLANNER",
            description="Decomposes high-level requirements into dependency-bounded DAGs with contracts.",
            allowed_tools=[],
            model_capability=ModelCapability.REASONING.value,
            max_execution_time_seconds=120,
            max_tool_calls=0,
            version="1.0.0",
            capabilities=["dag_planning", "contract_scoping", "dependency_analysis"],
        )
    )

    return registry

