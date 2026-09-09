"""Cognitive Reasoning modes, hypothesis testing, and structured decision factors for Kairo Cognitive Planning (Task 41).

Enforces:
1. Seven canonical reasoning modes (DIRECT, DECOMPOSITION, COMPARISON, DIAGNOSTIC, RESEARCH, ITERATIVE, LONG_HORIZON).
2. Diagnostic hypothesis formulation with lowest-risk test selection.
3. Read-first principle (observe before modifying).
4. Strict privacy boundary (never persist or expose raw chain-of-thought; only structured rationale).
"""

from enum import Enum
from typing import Any
import uuid
from pydantic import BaseModel, ConfigDict, Field


class ReasoningMode(str, Enum):
    """Canonical reasoning strategies supported by Kairo."""

    DIRECT = "DIRECT"                    # Simple goal: minimal overhead, single atomic step
    DECOMPOSITION = "DECOMPOSITION"      # Complex goal: multi-step DAG plan
    COMPARISON = "COMPARISON"            # Evaluate trade-offs among alternative approaches
    DIAGNOSTIC = "DIAGNOSTIC"            # Observe -> hypothesize -> lowest-risk test
    RESEARCH = "RESEARCH"                # Retrieve and synthesize verified evidence before deciding
    ITERATIVE = "ITERATIVE"              # Step-by-step feedback loop: act -> observe -> adapt
    LONG_HORIZON = "LONG_HORIZON"        # Extended task with checkpoints, periodic refresh, budgets


class Hypothesis(BaseModel):
    """A plausible candidate cause in diagnostic reasoning."""

    model_config = ConfigDict(extra="ignore")

    hypothesis_id: str = Field(default_factory=lambda: f"hyp_{uuid.uuid4().hex[:8]}")
    description: str = Field(..., description="Statement of candidate cause")
    likelihood: str = Field(default="MEDIUM", description="LOW, MEDIUM, HIGH")
    distinguishing_test: str = Field(..., description="Action/inspection to confirm or refute hypothesis")
    test_risk: str = Field(default="READ", description="Risk tier of the distinguishing test (prefer READ)")
    confirmed: bool | None = Field(default=None)
    evidence: str | None = Field(default=None)


class DecisionFactors(BaseModel):
    """Structured rationale explaining a planning choice without exposing private chain-of-thought."""

    model_config = ConfigDict(extra="ignore")

    goal_summary: str
    selected_mode: ReasoningMode
    key_evidence: list[str] = Field(default_factory=list)
    identified_unknowns: list[str] = Field(default_factory=list)
    risk_consideration: str
    tradeoffs_evaluated: list[str] = Field(default_factory=list)
    verification_strategy: str


class ReasoningEngine:
    """Classifies objectives into reasoning modes and coordinates structured diagnostic hypotheses."""

    @staticmethod
    def select_mode(goal_text: str, goal_type: str, is_complex: bool = False) -> ReasoningMode:
        """Deterministically choose the appropriate reasoning mode."""
        text_lower = goal_text.lower()

        # 1. Diagnostic triggers (fix, error, fail, debug, crash, bug)
        if any(w in text_lower for w in ("fix", "failing", "error", "debug", "crash", "investigate", "why")):
            return ReasoningMode.DIAGNOSTIC

        # 2. Research triggers (find, search, compare, research, literature, latest)
        if any(w in text_lower for w in ("research", "search", "literature", "compare", "latest news", "study")):
            return ReasoningMode.RESEARCH

        # 3. Long-horizon triggers (migration, refactor, deploy, pipeline, release)
        if any(w in text_lower for w in ("migrate", "refactor whole", "full release", "long-running", "production readiness")):
            return ReasoningMode.LONG_HORIZON

        # 4. Direct triggers (simple status, check time, simple read)
        if not is_complex and len(goal_text.split()) < 6 and any(w in text_lower for w in ("status", "time", "date", "version", "ping")):
            return ReasoningMode.DIRECT

        # Default to structured decomposition
        return ReasoningMode.DECOMPOSITION

    @staticmethod
    def generate_diagnostic_hypotheses(problem_description: str) -> list[Hypothesis]:
        """Generate candidate hypotheses with lowest-risk distinguishing tests (Read-First)."""
        desc_lower = problem_description.lower()
        hypotheses = []

        if "ci" in desc_lower or "test" in desc_lower:
            hypotheses.append(
                Hypothesis(
                    description="Repository test failure caused by recent code change.",
                    likelihood="HIGH",
                    distinguishing_test="Inspect latest git log and test error logs (READ)",
                    test_risk="READ",
                )
            )
            hypotheses.append(
                Hypothesis(
                    description="Environment or dependency outage (e.g. package index down, missing secret).",
                    likelihood="MEDIUM",
                    distinguishing_test="Check CI runner environment variables and network status (READ)",
                    test_risk="READ",
                )
            )
        elif "connection" in desc_lower or "database" in desc_lower or "500" in desc_lower:
            hypotheses.append(
                Hypothesis(
                    description="Service backend or database endpoint unavailable.",
                    likelihood="HIGH",
                    distinguishing_test="Query service health probe /health/ready (READ)",
                    test_risk="READ",
                )
            )
            hypotheses.append(
                Hypothesis(
                    description="Invalid credentials or configuration parameter.",
                    likelihood="MEDIUM",
                    distinguishing_test="Verify environment configuration loading (READ)",
                    test_risk="READ",
                )
            )
        else:
            hypotheses.append(
                Hypothesis(
                    description="System configuration drift or unexpected state divergence.",
                    likelihood="MEDIUM",
                    distinguishing_test="Inspect authoritative world state snapshot (READ)",
                    test_risk="READ",
                )
            )

        return hypotheses
