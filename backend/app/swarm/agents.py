"""Agent catalog, specialization definitions, health management, and capability-authorization boundaries (Task 64)."""

from __future__ import annotations

import logging
from typing import Any

from app.swarm.schemas import AgentHealthState, SwarmAgentSpec

logger = logging.getLogger(__name__)

# Canonical specialized agents for collective reasoning
DEFAULT_SWARM_AGENTS = [
    SwarmAgentSpec(
        agent_id="ag_architect",
        name="System Architect",
        role="ARCHITECT",
        description="Evaluates architectural structures, distributed state tradeoffs, and component boundaries.",
        capabilities=["system_design", "tradeoff_evaluation", "modularity_analysis", "scalability_modeling"],
        limitations=["cannot execute shell commands", "cannot modify production infrastructure"],
        tools=["code_read_file", "code_search"],
        permissions=["read_system_architecture"],
        trust_level=0.92,
        specialization="distributed_systems",
        health=AgentHealthState.HEALTHY,
        cost_profile=1.2,
        latency_profile_ms=600.0,
    ),
    SwarmAgentSpec(
        agent_id="ag_security_analyst",
        name="Security Analyst",
        role="SECURITY_ANALYST",
        description="Analyzes threat surfaces, authentication invariants, and secret containment boundaries.",
        capabilities=["threat_modeling", "vulnerability_audit", "permission_scoping", "injection_analysis"],
        limitations=["cannot grant credentials", "cannot modify authorization policies"],
        tools=["code_read_file", "code_search"],
        permissions=["read_security_posture"],
        trust_level=0.95,
        specialization="system_security",
        health=AgentHealthState.HEALTHY,
        cost_profile=1.1,
        latency_profile_ms=550.0,
    ),
    SwarmAgentSpec(
        agent_id="ag_critic",
        name="Devil's Advocate & Critic",
        role="CRITIC",
        description="Challenges assumptions, searches for counterarguments, and probes catastrophic failure modes.",
        capabilities=[
            "adversarial_review",
            "counter_argumentation",
            "edge_case_detection",
            "skeptical_audit",
        ],
        limitations=["does not produce authoritative consensus alone"],
        tools=["code_read_file"],
        permissions=["read_general_context"],
        trust_level=0.90,
        specialization="adversarial_analysis",
        health=AgentHealthState.HEALTHY,
        cost_profile=0.9,
        latency_profile_ms=450.0,
    ),
    SwarmAgentSpec(
        agent_id="ag_researcher",
        name="Evidence Researcher",
        role="RESEARCHER",
        description="Gathers verified empirical papers, benchmark specifications, and technical citations.",
        capabilities=[
            "information_retrieval",
            "source_verification",
            "literature_review",
            "citation_lineage",
        ],
        limitations=["cannot execute arbitrary web actions", "passive data only"],
        tools=["web_search", "web_fetch"],
        permissions=["read_external_sources"],
        trust_level=0.88,
        specialization="empirical_research",
        health=AgentHealthState.HEALTHY,
        cost_profile=1.0,
        latency_profile_ms=800.0,
    ),
    SwarmAgentSpec(
        agent_id="ag_fact_checker",
        name="Fact Checker",
        role="FACT_CHECKER",
        description="Verifies claims against primary sources and flags ungrounded assertions.",
        capabilities=["claim_validation", "primary_source_verification", "statistical_check"],
        limitations=["cannot alter underlying evidence"],
        tools=["code_read_file"],
        permissions=["read_general_context"],
        trust_level=0.94,
        specialization="fact_verification",
        health=AgentHealthState.HEALTHY,
        cost_profile=0.8,
        latency_profile_ms=400.0,
    ),
    SwarmAgentSpec(
        agent_id="ag_risk_analyst",
        name="Risk & Reliability Analyst",
        role="RISK_ANALYST",
        description="Evaluates operational blast radius, cascading failure risks, and recovery timeouts.",
        capabilities=["failure_mode_analysis", "blast_radius_containment", "recovery_assessment"],
        limitations=["cannot execute mitigation steps directly"],
        tools=["code_read_file"],
        permissions=["read_system_telemetry"],
        trust_level=0.91,
        specialization="resilience_engineering",
        health=AgentHealthState.HEALTHY,
        cost_profile=1.0,
        latency_profile_ms=500.0,
    ),
    SwarmAgentSpec(
        agent_id="ag_synthesizer",
        name="Collective Synthesizer",
        role="SYNTHESIZER",
        description="Reconciles diverse perspectives, structures evidence-weighted consensus, and preserves minority views.",
        capabilities=[
            "consensus_formation",
            "disagreement_reconciliation",
            "executive_reporting",
            "evidence_weighting",
        ],
        limitations=["cannot bypass TruthVerifier"],
        tools=[],
        permissions=["read_agent_results"],
        trust_level=0.93,
        specialization="synthesis_and_consensus",
        health=AgentHealthState.HEALTHY,
        cost_profile=1.3,
        latency_profile_ms=650.0,
    ),
    SwarmAgentSpec(
        agent_id="ag_verifier",
        name="Truth & Contract Verifier",
        role="VERIFIER",
        description="Executes formal verification checks against ground truth criteria and safety invariants.",
        capabilities=["formal_verification", "truth_audit", "contract_validation"],
        limitations=["cannot grant operational sign-off alone"],
        tools=["code_read_file"],
        permissions=["read_system_contracts"],
        trust_level=0.98,
        specialization="verification_and_correctness",
        health=AgentHealthState.HEALTHY,
        cost_profile=1.0,
        latency_profile_ms=500.0,
    ),
    SwarmAgentSpec(
        agent_id="ag_optimizer",
        name="Performance Optimizer",
        role="OPTIMIZER",
        description="Profiles throughput, memory footprint, cache hit ratios, and computational complexity.",
        capabilities=["profiling", "latency_reduction", "resource_optimization", "throughput_modeling"],
        limitations=["cannot modify live runtime settings without policy approval"],
        tools=["code_read_file"],
        permissions=["read_system_metrics"],
        trust_level=0.91,
        specialization="performance_engineering",
        health=AgentHealthState.HEALTHY,
        cost_profile=1.1,
        latency_profile_ms=450.0,
    ),
    SwarmAgentSpec(
        agent_id="ag_forecaster",
        name="Predictive Forecaster",
        role="FORECASTER",
        description="Forecasts future state, capacity exhaustion, and operational trends under variable workloads.",
        capabilities=["trend_extrapolation", "capacity_forecasting", "variance_modeling"],
        limitations=["cannot guarantee probabilistic outcomes as deterministic facts"],
        tools=["code_read_file"],
        permissions=["read_historical_telemetry"],
        trust_level=0.89,
        specialization="forecasting",
        health=AgentHealthState.HEALTHY,
        cost_profile=1.0,
        latency_profile_ms=550.0,
    ),
    SwarmAgentSpec(
        agent_id="ag_incident_responder",
        name="Incident Responder",
        role="INCIDENT_RESPONDER",
        description="Analyzes failure triage, containment blast radius, and rollback verification.",
        capabilities=["incident_triage", "containment_planning", "recovery_checkpointing"],
        limitations=["cannot execute destructive containment without human approval"],
        tools=["code_read_file"],
        permissions=["read_incident_logs"],
        trust_level=0.93,
        specialization="incident_response",
        health=AgentHealthState.HEALTHY,
        cost_profile=1.2,
        latency_profile_ms=400.0,
    ),
]


class SwarmAgentRegistry:
    """Manages available swarm agents, health tracking, and capability-authorization boundaries (Spec 5, 6, 7)."""

    def __init__(self) -> None:
        self._agents: dict[str, SwarmAgentSpec] = {}
        self._performance_history: dict[str, list[dict[str, Any]]] = {}
        self._seed_default_agents()

    def _seed_default_agents(self) -> None:
        for ag in DEFAULT_SWARM_AGENTS:
            self._agents[ag.agent_id] = ag.model_copy(deep=True)
            self._performance_history[ag.agent_id] = []

    def register_agent(self, agent: SwarmAgentSpec) -> SwarmAgentSpec:
        """Register or update an agent specification with provenance."""
        self._agents[agent.agent_id] = agent
        if agent.agent_id not in self._performance_history:
            self._performance_history[agent.agent_id] = []
        logger.info("SWARM_AGENT_REGISTERED: id=%s role=%s name=%s", agent.agent_id, agent.role, agent.name)
        return agent

    def register(self, agent: SwarmAgentSpec) -> SwarmAgentSpec:
        """Alias for register_agent."""
        return self.register_agent(agent)

    def disable_agent(self, agent_id: str) -> SwarmAgentSpec:
        """Disable an agent from participation."""
        return self.update_health(agent_id, AgentHealthState.DISABLED)

    def list_available(self) -> list[SwarmAgentSpec]:
        """List operational healthy agents."""
        return [a for a in self._agents.values() if a.health == AgentHealthState.HEALTHY]

    def get_agent(self, agent_id: str) -> SwarmAgentSpec | None:
        """Retrieve agent by ID."""
        return self._agents.get(agent_id)

    def list_agents(
        self,
        role: str | None = None,
        health: AgentHealthState | None = None,
        capability: str | None = None,
    ) -> list[SwarmAgentSpec]:
        """List registered agents matching optional filters."""
        results = list(self._agents.values())
        if role:
            results = [a for a in results if a.role.upper() == role.upper()]
        if health:
            results = [a for a in results if a.health == health]
        if capability:
            results = [a for a in results if capability.lower() in [c.lower() for c in a.capabilities]]
        return results

    def update_health(self, agent_id: str, health: AgentHealthState) -> SwarmAgentSpec:
        """Update an agent's health state (Invariant: UNKNOWN != HEALTHY)."""
        agent = self.get_agent(agent_id)
        if not agent:
            raise KeyError(f"Agent '{agent_id}' not found in registry.")
        agent.health = health
        logger.info("SWARM_AGENT_HEALTH_UPDATED: id=%s health=%s", agent_id, health.value)
        return agent

    def is_agent_healthy(self, agent_id: str) -> bool:
        """Strict check: only HEALTHY is considered operational. UNKNOWN != HEALTHY."""
        agent = self.get_agent(agent_id)
        if not agent:
            return False
        return agent.health == AgentHealthState.HEALTHY

    def check_authorization(self, agent_id: str, required_permission: str) -> bool:
        """Invariant: CAPABILITY != AUTHORIZATION.

        Possessing a capability (e.g. security analysis) NEVER implies possessing an authorization.
        """
        agent = self.get_agent(agent_id)
        if not agent:
            return False
        return required_permission in agent.permissions or "*" in agent.permissions

    def record_performance(
        self,
        agent_id: str,
        task_id: str,
        success: bool,
        latency_ms: float,
        confidence: float,
        verification_passed: bool,
    ) -> None:
        """Track agent performance for calibration and drift detection (Spec 49 & 50)."""
        if agent_id not in self._performance_history:
            self._performance_history[agent_id] = []
        record = {
            "task_id": task_id,
            "success": success,
            "latency_ms": latency_ms,
            "confidence": confidence,
            "verification_passed": verification_passed,
        }
        self._performance_history[agent_id].append(record)


swarm_agent_registry = SwarmAgentRegistry()
