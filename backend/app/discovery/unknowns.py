"""Unknown Detection and Research Question Formulation (Task 72).

Identifies epistemic gaps (KNOWN, UNKNOWN, UNCERTAIN, CONFLICTING, UNVERIFIED)
from reasoning, context, and environment, and formulates disciplined, decision-relevant
research questions.
"""

import uuid
from typing import Any

from app.discovery.schemas import EpistemicCategory, ResearchQuestion


class UnknownDetector:
    """Discovers knowledge gaps and determines if they warrant scientific investigation."""

    def __init__(self, min_importance: float = 0.5, min_uncertainty: float = 0.4):
        self.min_importance = min_importance
        self.min_uncertainty = min_uncertainty

    def detect_epistemic_gaps(
        self,
        knowns: list[str] | None = None,
        unknowns: list[str] | None = None,
        uncertains: list[str] | None = None,
        conflicting: list[str] | None = None,
        unverified: list[str] | None = None,
    ) -> dict[EpistemicCategory, list[str]]:
        """Categorizes propositions strictly following epistemic principles."""
        return {
            EpistemicCategory.KNOWN: list(knowns or []),
            EpistemicCategory.UNKNOWN: list(unknowns or []),
            EpistemicCategory.UNCERTAIN: list(uncertains or []),
            EpistemicCategory.CONFLICTING: list(conflicting or []),
            EpistemicCategory.UNVERIFIED: list(unverified or []),
        }

    def evaluate_investigation_warrant(
        self,
        candidate_question: str,
        importance: float,
        uncertainty: float,
        decision_relevance: bool,
    ) -> bool:
        """Determines if an unknown warrants an autonomous scientific investigation.

        Strict Principle: Do NOT automatically turn every unknown into an experiment.
        Only high-importance, genuinely uncertain, and decision-relevant unknowns are investigated.
        """
        if not candidate_question.strip():
            return False
        if not decision_relevance:
            return False
        return importance >= self.min_importance and uncertainty >= self.min_uncertainty

    def formulate_question(
        self,
        question_text: str,
        scope: str = "system",
        importance: float = 0.8,
        uncertainty: float = 0.7,
        goal_alignment: str = "",
        decision_relevance: bool = True,
        time_constraints: str | None = None,
        required_evidence: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ResearchQuestion:
        """Constructs a structured ResearchQuestion."""
        q_id = f"rq_{uuid.uuid4().hex[:12]}"
        return ResearchQuestion(
            question_id=q_id,
            question=question_text.strip(),
            scope=scope,
            importance=max(0.0, min(1.0, float(importance))),
            uncertainty=max(0.0, min(1.0, float(uncertainty))),
            goal_alignment=goal_alignment,
            decision_relevance=decision_relevance,
            time_constraints=time_constraints,
            required_evidence=list(required_evidence or []),
            status="OPEN",
            metadata=metadata or {},
        )

    def extract_from_reasoning_session(
        self,
        reasoning_data: dict[str, Any],
    ) -> list[ResearchQuestion]:
        """Extracts actionable candidate research questions from a Task 71 reasoning session."""
        questions: list[ResearchQuestion] = []
        uncertainties = reasoning_data.get("uncertainties", [])
        evidence_gaps = reasoning_data.get("evidence_gaps", [])

        # Process uncertainties
        for item in uncertainties:
            desc = item if isinstance(item, str) else item.get("description", "")
            if not desc:
                continue
            # Formulate clear empirical question
            q_text = f"Can we empirically determine: {desc}?" if not desc.endswith("?") else desc
            if self.evaluate_investigation_warrant(
                q_text, importance=0.8, uncertainty=0.7, decision_relevance=True
            ):
                questions.append(
                    self.formulate_question(
                        question_text=q_text,
                        scope="reasoning_gap",
                        importance=0.8,
                        uncertainty=0.7,
                        goal_alignment=str(reasoning_data.get("objective", "")),
                        decision_relevance=True,
                        required_evidence=["empirical_observation", "counterfactual_check"],
                    )
                )

        # Process evidence gaps
        for gap in evidence_gaps:
            desc = gap if isinstance(gap, str) else gap.get("gap", "")
            if not desc:
                continue
            q_text = f"What is the empirical evidence regarding {desc}?"
            questions.append(
                self.formulate_question(
                    question_text=q_text,
                    scope="evidence_gap",
                    importance=0.75,
                    uncertainty=0.8,
                    goal_alignment=str(reasoning_data.get("objective", "")),
                    decision_relevance=True,
                )
            )

        return questions
