"""Candidate option generation, completeness verification, and option categorization."""

from __future__ import annotations

import uuid
from typing import Any

from app.decision.schemas import CandidateOption, OptionType, ReversibilityLevel


class OptionGenerator:
    """Generates a diverse, complete set of candidate options including conservative, reversible, and baseline options."""

    def generate_options(
        self,
        question: str,
        context: dict[str, Any],
        custom_options: list[CandidateOption] | None = None,
    ) -> list[CandidateOption]:
        """Ensures complete option space covering conservative, aggressive, reversible, info-gathering, and baseline."""
        options: list[CandidateOption] = list(custom_options or [])

        # Check if baseline (NO_ACTION) exists; if not, add it
        has_no_action = any(opt.option_type == OptionType.NO_ACTION for opt in options)
        if not has_no_action:
            options.append(
                CandidateOption(
                    option_id=f"opt_baseline_{uuid.uuid4().hex[:6]}",
                    name="Maintain Current State (No Action)",
                    description="Do nothing immediately. Maintain existing operational state and monitor metrics.",
                    option_type=OptionType.NO_ACTION,
                    reversibility=ReversibilityLevel.REVERSIBLE,
                    metrics={"cost": 0.0, "risk": 0.2, "reliability": 0.7, "latency": 50.0, "security": 0.8},
                )
            )

        # Check if information gathering option exists
        has_info = any(opt.option_type == OptionType.INFO_GATHERING for opt in options)
        if not has_info:
            options.append(
                CandidateOption(
                    option_id=f"opt_diag_{uuid.uuid4().hex[:6]}",
                    name="Run In-Depth Diagnostic Telemetry Probe",
                    description="Collect additional metrics and run digital twin simulation before applying physical changes.",
                    option_type=OptionType.INFO_GATHERING,
                    reversibility=ReversibilityLevel.REVERSIBLE,
                    metrics={"cost": 5.0, "risk": 0.1, "reliability": 0.85, "latency": 52.0, "security": 0.9},
                )
            )

        # Check if conservative option exists
        has_conservative = any(opt.option_type == OptionType.CONSERVATIVE for opt in options)
        if not has_conservative:
            options.append(
                CandidateOption(
                    option_id=f"opt_cons_{uuid.uuid4().hex[:6]}",
                    name="Conservative Remediation",
                    description="Apply minimal bounded changes with immediate automated rollback guards.",
                    option_type=OptionType.CONSERVATIVE,
                    reversibility=ReversibilityLevel.REVERSIBLE,
                    metrics={"cost": 20.0, "risk": 0.2, "reliability": 0.90, "latency": 35.0, "security": 0.85},
                )
            )

        # Check if progressive / aggressive option exists
        has_aggressive = any(opt.option_type == OptionType.AGGRESSIVE for opt in options)
        if not has_aggressive:
            options.append(
                CandidateOption(
                    option_id=f"opt_aggr_{uuid.uuid4().hex[:6]}",
                    name="Full Scale-Out Optimization",
                    description="Scale infrastructure to maximum provisioned quotas to guarantee zero queuing delay.",
                    option_type=OptionType.AGGRESSIVE,
                    reversibility=ReversibilityLevel.PARTIALLY_REVERSIBLE,
                    metrics={"cost": 85.0, "risk": 0.45, "reliability": 0.98, "latency": 15.0, "security": 0.88},
                )
            )

        return options

    def ensure_option_space(
        self,
        provided_options: list[CandidateOption],
        request_intent: str | None = None,
    ) -> list[CandidateOption]:
        """Ensures a complete, well-diversified set of candidate options."""
        return self.generate_options(
            question=request_intent or "default_intent",
            context={},
            custom_options=provided_options,
        )


option_generator = OptionGenerator()

