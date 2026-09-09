"""Agent capability definitions and authorization boundary distinction (Task 44)."""

from __future__ import annotations

from enum import Enum
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("kairo.agents.capabilities")


class CapabilityType(str, Enum):
    REASONING = "REASONING"
    TOOL_REQUEST = "TOOL_REQUEST"
    OUTPUT_GENERATION = "OUTPUT_GENERATION"


@dataclass
class AgentCapability:
    """Formal definition of what an agent can reason about, request, and produce (Spec 4)."""

    capability_id: str
    name: str
    description: str
    reasoning_domains: list[str] = field(default_factory=list)
    requested_tool_categories: list[str] = field(default_factory=list)
    produced_output_types: list[str] = field(default_factory=list)
    risk_level: str = "LOW"  # LOW, MEDIUM, HIGH, CRITICAL

    def to_dict(self) -> dict[str, Any]:
        return {
            "capability_id": self.capability_id,
            "name": self.name,
            "description": self.description,
            "reasoning_domains": self.reasoning_domains,
            "requested_tool_categories": self.requested_tool_categories,
            "produced_output_types": self.produced_output_types,
            "risk_level": self.risk_level,
        }


class CapabilityRegistry:
    """Standardized catalog of agent capabilities.
    
    PRINCIPLE: Capability is NOT Authorization (Spec 5).
    An agent capable of file modification or cloud deployment does NOT imply permission to do so.
    Permissions are strictly verified against PolicyEngine and active AgentContract.
    """

    def __init__(self) -> None:
        self._capabilities: dict[str, AgentCapability] = {}
        self._seed_default_capabilities()

    def _seed_default_capabilities(self) -> None:
        defaults = [
            AgentCapability(
                capability_id="cap_code_ast",
                name="AST Code Manipulation",
                description="Syntactic analysis and safe refactoring using AST parsers.",
                reasoning_domains=["coding", "refactoring", "syntax"],
                requested_tool_categories=["code_read", "code_search", "code_analyze"],
                produced_output_types=["diff", "syntax_tree", "patch_proposal"],
                risk_level="LOW",
            ),
            AgentCapability(
                capability_id="cap_security_audit",
                name="Security & Vulnerability Audit",
                description="Static analysis for secrets, SQLi, XSS, and authorization leaks.",
                reasoning_domains=["security", "audit", "compliance"],
                requested_tool_categories=["code_analyze", "security_scan"],
                produced_output_types=["vulnerability_report", "risk_assessment"],
                risk_level="MEDIUM",
            ),
            AgentCapability(
                capability_id="cap_web_research",
                name="Web & Documentation Research",
                description="Retrieving and triangulating information from public technical sources.",
                reasoning_domains=["research", "documentation", "citations"],
                requested_tool_categories=["web_search", "web_fetch"],
                produced_output_types=["evidence_dossier", "citation_list"],
                risk_level="LOW",
            ),
            AgentCapability(
                capability_id="cap_test_verification",
                name="Automated Test Verification",
                description="Executing unit, integration, and invariant tests to verify claims.",
                reasoning_domains=["testing", "verification", "regression"],
                requested_tool_categories=["test_runner", "pytest"],
                produced_output_types=["test_report", "verification_proof"],
                risk_level="MEDIUM",
            ),
            AgentCapability(
                capability_id="cap_system_deploy",
                name="Infrastructure & Service Deployment",
                description="Staging and deploying containers, services, and configuration.",
                reasoning_domains=["deployment", "infrastructure", "devops"],
                requested_tool_categories=["docker", "kubectl", "system_exec"],
                produced_output_types=["deployment_status", "rollback_probe"],
                risk_level="CRITICAL",
            ),
        ]
        for cap in defaults:
            self.register(cap)

    def register(self, capability: AgentCapability) -> None:
        self._capabilities[capability.capability_id.lower()] = capability

    def get(self, capability_id: str) -> AgentCapability | None:
        return self._capabilities.get(capability_id.lower())

    def list_capabilities(self) -> list[AgentCapability]:
        return list(self._capabilities.values())
