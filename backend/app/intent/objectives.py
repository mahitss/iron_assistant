"""Measurable Objectives, Measurable Sub-Outcomes, and Success Criteria Extraction (Task 48)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import logging
import re
from typing import Any, Dict, List, Optional
import uuid

logger = logging.getLogger("kairo.intent.objectives")


class ObjectiveType(str, Enum):
    """Classification of measurable sub-outcome types."""

    QUANTITATIVE = "QUANTITATIVE"
    QUALITATIVE = "QUALITATIVE"
    BOOLEAN = "BOOLEAN"
    MILESTONE = "MILESTONE"


@dataclass
class Objective:
    """Measurable sub-outcome contributing to an overarching user goal (Spec 11-14)."""

    description: str
    objective_id: str = field(default_factory=lambda: f"obj_{uuid.uuid4().hex[:8]}")
    objective_type: ObjectiveType = ObjectiveType.QUALITATIVE
    target_metric: Optional[str] = None
    target_value: Optional[str] = None
    is_inferred: bool = False  # Enforce Spec 13: mark implied success as inferred
    status: str = "PENDING"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "objective_id": self.objective_id,
            "description": self.description,
            "objective_type": self.objective_type.value,
            "target_metric": self.target_metric,
            "target_value": self.target_value,
            "is_inferred": self.is_inferred,
            "status": self.status,
            "metadata": self.metadata,
        }


class ObjectiveExtractor:
    """Extracts explicit and inferred measurable objectives from user statements (Spec 11-14).
    
    CRITICAL INVARIANT (Spec 14):
    Never fabricate arbitrary requirements or invent ungrounded success criteria.
    """

    # Patterns for quantitative goals: e.g. "load under 2 seconds", "coverage above 80%", "error rate < 1%"
    METRIC_PATTERNS = [
        (re.compile(r"\b(?:load|latency|response\s*time)\s*(under|<|below|less\s*than)\s*([\d\.]+\s*(?:seconds|minutes|ms|s)?)", re.IGNORECASE), "latency"),
        (re.compile(r"\b(?:coverage|test\s*coverage)\s*(above|>|greater\s*than|at\s*least)\s*([\d\.]+\s*%)", re.IGNORECASE), "test_coverage"),
        (re.compile(r"\b(?:cost|spend|budget)\s*(under|<|below|within)\s*([\$€£]?\s*[\d\.]+)", re.IGNORECASE), "budget_limit"),
        (re.compile(r"\b(?:error\s*rate|failure\s*rate)\s*(below|<|under)\s*([\d\.]+\s*%)", re.IGNORECASE), "error_rate"),
        (re.compile(r"\b(?:uptime|availability)\s*(above|>|at\s*least)\s*([\d\.]+\s*%)", re.IGNORECASE), "availability"),
    ]


    @classmethod
    def extract_objectives(cls, raw_text: str, is_inferred: bool = False) -> List[Objective]:
        objectives: List[Objective] = []

        # 1. Match quantitative success criteria
        for pattern, metric_name in cls.METRIC_PATTERNS:
            match = pattern.search(raw_text)
            if match:
                val = match.group(2).strip()
                desc = f"Ensure {metric_name} meets target {val}"
                objectives.append(
                    Objective(
                        description=desc,
                        objective_type=ObjectiveType.QUANTITATIVE,
                        target_metric=metric_name,
                        target_value=val,
                        is_inferred=is_inferred,
                    )
                )

        # 2. General operational sub-outcomes if no explicit numeric metric found

        if not objectives:
            # Generate grounded objective strictly from text (Spec 14: no fabrication)
            objectives.append(
                Objective(
                    description=raw_text.strip(),
                    target_metric=None,
                    target_value=None,
                    is_inferred=is_inferred,
                )
            )

        return objectives
