"""Safe User Motivation Engine, Functional Motivator Detection, and Tradeoff Modeling (Task 48)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
import re
from typing import Any, Dict, List, Optional
import uuid

from app.intent.schemas import MotivationCategory

logger = logging.getLogger("kairo.intent.motivation")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class MotivationSignal:
    """Safe, strictly functional motivator (Spec 76-80).
    
    CRITICAL INVARIANT (Spec 77):
    Motivation != Psychological Diagnosis!
    Strictly forbidden from inferring sensitive personal traits, mood, politics, or mental states.
    Motivation is solely used to help rank execution options and cannot override explicit user instructions (Spec 80).
    """

    category: MotivationCategory
    confidence: float = 0.8
    evidence: List[str] = field(default_factory=list)
    motivation_id: str = field(default_factory=lambda: f"mot_{uuid.uuid4().hex[:8]}")
    created_at: datetime = field(default_factory=utc_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "motivation_id": self.motivation_id,
            "category": self.category.value,
            "confidence": round(self.confidence, 3),
            "evidence": self.evidence,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class TradeoffAnalysis:
    """Explicitly surfaced tradeoff when multiple goals or constraints conflict (Spec 82-84).
    
    CRITICAL INVARIANT (Spec 84):
    No hidden optimization! Do not optimize for unspoken objectives when consequences are material.
    """

    analysis_id: str = field(default_factory=lambda: f"tradeoff_{uuid.uuid4().hex[:8]}")
    conflicting_goals: List[str] = field(default_factory=list)
    options: List[Dict[str, Any]] = field(default_factory=list)
    recommended_option: Optional[str] = None
    requires_user_decision: bool = True
    preferred_goal: str = ""
    cost_difference: float = 0.0
    benefit_difference: str = ""
    recommendation: str = ""
    created_at: datetime = field(default_factory=utc_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "analysis_id": self.analysis_id,
            "conflicting_goals": self.conflicting_goals,
            "options": self.options,
            "recommended_option": self.recommended_option,
            "requires_user_decision": self.requires_user_decision,
            "preferred_goal": self.preferred_goal,
            "cost_difference": self.cost_difference,
            "benefit_difference": self.benefit_difference,
            "recommendation": self.recommendation,
            "created_at": self.created_at.isoformat(),
        }


class MotivationEngine:
    """Extracts safe functional motivators and computes explicit tradeoff analyses (Spec 76-85)."""

    @classmethod
    def analyze_tradeoff(
        cls,
        goal_a: str,
        goal_b: str,
        cost_a: float = 0.0,
        cost_b: float = 0.0,
        benefit_a: str = "",
        benefit_b: str = "",
        constraints: Optional[List[str]] = None,
    ) -> TradeoffAnalysis:
        """Enforce Spec 82-84: Explicitly model tradeoffs between competing user goals."""
        cost_diff = abs(cost_b - cost_a)
        # Check safety preference
        if "safety" in goal_b.lower() or "regression" in goal_b.lower() or "reliable" in goal_b.lower():
            preferred = goal_b
            rec = f"Recommend prioritizing '{goal_b}' due to reliability and safety verification requirements."
        else:
            preferred = goal_a if cost_a <= cost_b else goal_b
            rec = f"Recommend prioritizing '{preferred}' based on explicit resource constraints."

        options = [
            {"name": goal_a, "cost": cost_a, "benefit": benefit_a or f"Fulfills {goal_a}"},
            {"name": goal_b, "cost": cost_b, "benefit": benefit_b or f"Fulfills {goal_b}"},
        ]
        return TradeoffAnalysis(
            conflicting_goals=[goal_a, goal_b],
            options=options,
            preferred_goal=preferred,
            cost_difference=cost_diff,
            benefit_difference=benefit_b or f"Benefit comparison for {preferred}",
            recommendation=rec,
            recommended_option=preferred,
            requires_user_decision=True,
        )


    CATEGORY_PATTERNS = [
        (MotivationCategory.EFFICIENCY, re.compile(r"\b(fast|speed|faster|optimize|efficient|quick|overhead)\b", re.IGNORECASE)),
        (MotivationCategory.QUALITY, re.compile(r"\b(clean|quality|best practice|robust|reliable|maintainable)\b", re.IGNORECASE)),
        (MotivationCategory.SAFETY, re.compile(r"\b(safe|secure|protect|verify|careful|backup|test)\b", re.IGNORECASE)),
        (MotivationCategory.LEARNING, re.compile(r"\b(learn|explain|understand|how does|why|tutorial)\b", re.IGNORECASE)),
        (MotivationCategory.TIME_SAVING, re.compile(r"\b(save time|automate|routine|repetitive|hands-free)\b", re.IGNORECASE)),
        (MotivationCategory.CONVENIENCE, re.compile(r"\b(simple|easy|straightforward|usual|default)\b", re.IGNORECASE)),
        (MotivationCategory.COMPLETION, re.compile(r"\b(finish|done|complete|wrap up|finalize)\b", re.IGNORECASE)),
        (MotivationCategory.CREATION, re.compile(r"\b(build|create|scaffold|generate|design)\b", re.IGNORECASE)),
        (MotivationCategory.EXPLORATION, re.compile(r"\b(explore|investigate|options|compare|alternatives)\b", re.IGNORECASE)),
    ]

    @classmethod
    def detect_motivation(cls, text: str) -> List[MotivationSignal]:
        signals: List[MotivationSignal] = []

        for category, pat in cls.CATEGORY_PATTERNS:
            matches = pat.findall(text)
            if matches:
                signals.append(
                    MotivationSignal(
                        category=category,
                        confidence=0.85,
                        evidence=[f"Matched keywords: {', '.join(set(matches))}"],
                    )
                )

        return signals

    @classmethod
    def evaluate_tradeoff(
        cls,
        goal_a: str,
        goal_b: str,
        cost_impact: str,
        time_impact: str,
    ) -> TradeoffAnalysis:
        """Enforce Spec 82, 83: Surface tradeoff explicitly between conflicting goals."""
        options = [
            {
                "name": f"Prioritize {goal_a}",
                "description": f"Focus on {goal_a} at the expense of {goal_b}",
                "pros": [f"Maximizes {goal_a}"],
                "cons": [f"May compromise {goal_b}", cost_impact],
            },
            {
                "name": f"Prioritize {goal_b}",
                "description": f"Focus on {goal_b} while relaxing constraints on {goal_a}",
                "pros": [f"Satisfies {goal_b}"],
                "cons": [f"Suboptimal for {goal_a}", time_impact],
            },
            {
                "name": "Balanced Compromise",
                "description": "Adjust parameters to achieve acceptable baseline for both",
                "pros": ["Avoids extreme failure in either goal"],
                "cons": ["Takes longer to converge"],
            },
        ]
        return TradeoffAnalysis(
            conflicting_goals=[goal_a, goal_b],
            options=options,
            recommended_option="Balanced Compromise",
            requires_user_decision=True,
        )
