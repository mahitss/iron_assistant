"""Constraint Discovery, Hard vs Soft Classification, and Conflict Detection (Task 48)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from app.intent.schemas import ConstraintCategory, ConstraintPriority, ConstraintType

logger = logging.getLogger("kairo.intent.constraints")


@dataclass
class DiscoveredConstraint:
    """Individual constraint bound (Spec 15-19)."""

    name: str
    category: ConstraintCategory
    constraint_type: ConstraintType
    value: Any
    priority: int = 1  # 1 (highest) to 5 (lowest)
    description: str = ""
    is_negation: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "category": self.category.value,
            "constraint_type": self.constraint_type.value,
            "value": self.value,
            "priority": self.priority,
            "description": self.description,
            "is_negation": self.is_negation,
        }


class ConstraintConflictError(Exception):
    """Raised when mutually contradictory hard constraints are identified (Spec 18)."""


class ConstraintEngine:
    """Discovers, validates, and detects conflicts among operational constraints (Spec 15-19)."""

    # Detection patterns for constraints
    BUDGET_REGEX = re.compile(r"(budget|cost|spend)\s*(?:under|less than|max|within)\s*([\$€£]?\s*[\d\.]+)", re.IGNORECASE)
    TIME_REGEX = re.compile(r"(before|by|until|within|in)\s*(\d+\s*(?:hours|days|mins|minutes|pm|am|utc))", re.IGNORECASE)
    TECH_REGEX = re.compile(r"(use|using|with|in)\s*(python|fastapi|node|react|postgres|sqlite|docker|kubernetes)", re.IGNORECASE)
    FORMAT_REGEX = re.compile(r"(as|format|in)\s*(json|csv|markdown|yaml|pdf|table)", re.IGNORECASE)
    NEGATION_REGEX = re.compile(r"\b(don't|do not|never|without|exclude|except|no)\s+([a-zA-Z0-9_\-]+)", re.IGNORECASE)

    @classmethod
    def discover_constraints(cls, text: str, hard_default: bool = True) -> List[DiscoveredConstraint]:
        constraints: List[DiscoveredConstraint] = []

        # 1. Budget constraint
        m_b = cls.BUDGET_REGEX.search(text)
        if m_b:
            constraints.append(
                DiscoveredConstraint(
                    name="budget_limit",
                    category=ConstraintCategory.BUDGET,
                    constraint_type=ConstraintType.HARD if hard_default else ConstraintType.SOFT,
                    value=m_b.group(2).strip(),
                    description=f"Spending constrained to {m_b.group(2).strip()}",
                )
            )

        # 2. Time constraint
        m_t = cls.TIME_REGEX.search(text)
        if m_t:
            constraints.append(
                DiscoveredConstraint(
                    name="completion_deadline",
                    category=ConstraintCategory.TIME,
                    constraint_type=ConstraintType.HARD if hard_default else ConstraintType.SOFT,
                    value=m_t.group(2).strip(),
                    description=f"Action must complete by {m_t.group(2).strip()}",
                )
            )

        # 3. Tech stack constraint
        for m_tech in cls.TECH_REGEX.finditer(text):
            val = m_tech.group(2).strip()
            constraints.append(
                DiscoveredConstraint(
                    name=f"technology_{val.lower()}",
                    category=ConstraintCategory.TECHNOLOGY,
                    constraint_type=ConstraintType.HARD if "must" in text.lower() else ConstraintType.SOFT,
                    value=val,
                    description=f"Target technology specified as {val}",
                )
            )

        # 4. Format constraint
        m_f = cls.FORMAT_REGEX.search(text)
        if m_f:
            constraints.append(
                DiscoveredConstraint(
                    name="output_format",
                    category=ConstraintCategory.FORMAT,
                    constraint_type=ConstraintType.SOFT,
                    value=m_f.group(2).lower(),
                    description=f"Output presentation format: {m_f.group(2).lower()}",
                )
            )

        # 5. Negations (hard exclusion constraints)
        for m_neg in cls.NEGATION_REGEX.finditer(text):
            neg_target = m_neg.group(2).strip()
            constraints.append(
                DiscoveredConstraint(
                    name=f"exclude_{neg_target}",
                    category=ConstraintCategory.SCOPE,
                    constraint_type=ConstraintType.HARD,  # Negations are strictly HARD constraints (Spec 16, 97)
                    value=neg_target,
                    description=f"Explicit negation forbidding '{neg_target}'",
                    is_negation=True,
                )
            )

        return constraints

    @classmethod
    def check_conflicts(cls, constraints: List[DiscoveredConstraint]) -> List[Tuple[DiscoveredConstraint, DiscoveredConstraint, str]]:
        """Enforce Spec 18: Detect contradictory constraints."""
        conflicts = []
        n = len(constraints)
        for i in range(n):
            for j in range(i + 1, n):
                c1 = constraints[i]
                c2 = constraints[j]

                # Conflict 1: Include vs Exclude same target
                if c1.is_negation != c2.is_negation:
                    if str(c1.value).lower() == str(c2.value).lower():
                        conflicts.append((c1, c2, f"Direct contradiction: '{c1.name}' and '{c2.name}' both target '{c1.value}'"))

                # Conflict 2: Mutually exclusive formats
                if c1.category == ConstraintCategory.FORMAT and c2.category == ConstraintCategory.FORMAT:
                    if c1.value != c2.value:
                        conflicts.append((c1, c2, f"Conflicting output formats: '{c1.value}' vs '{c2.value}'"))

        if conflicts:
            logger.warning("Detected %d constraint conflicts: %s", len(conflicts), conflicts)
        return conflicts
