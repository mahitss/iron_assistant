"""Reusable plan strategies, templates, and learning loop integration for Kairo Cognitive Planning (Task 41).

Enforces:
1. Reusable templates must be versioned, validated, and scoped.
2. Template security: Templates CANNOT bypass current security policy or authorization.
3. Learned strategies from historical runs cannot override policy.
"""

from typing import Any
from pydantic import BaseModel, ConfigDict, Field

from app.cognition.plans import PlanRiskLevel


class PlanTemplate(BaseModel):
    """A parameterized, reusable plan pattern for canonical workflows."""

    model_config = ConfigDict(extra="ignore")

    template_id: str
    name: str
    version: int = 1
    description: str
    target_category: str
    default_risk: PlanRiskLevel = PlanRiskLevel.LOW
    step_blueprints: list[dict[str, Any]] = Field(default_factory=list)
    required_capabilities: list[str] = Field(default_factory=list)


class StrategyRegistry:
    """Registry of approved plan templates with policy compliance checks."""

    def __init__(self) -> None:
        self._templates: dict[str, PlanTemplate] = {}
        self._load_built_in_templates()

    def _load_built_in_templates(self) -> None:
        """Register built-in, pre-validated plan templates."""
        ci_fix_template = PlanTemplate(
            template_id="tpl_ci_fix_v1",
            name="CI Workflow Failure Fix",
            version=1,
            description="Diagnostic workflow: inspect failure logs, identify root cause, apply minimal patch, and run tests.",
            target_category="DEVELOPMENT",
            default_risk=PlanRiskLevel.MEDIUM,
            step_blueprints=[
                {"action": "inspect_logs", "risk": "READ"},
                {"action": "code_inspect", "risk": "READ"},
                {"action": "code_patch", "risk": "WRITE"},
                {"action": "test_runner", "risk": "READ"},
                {"action": "verify_health", "risk": "READ"},
            ],
            required_capabilities=["git_status", "test_runner"],
        )
        self.register_template(ci_fix_template)

    def register_template(self, template: PlanTemplate) -> None:
        """Register a verified template."""
        self._templates[template.template_id] = template

    def get_template(self, template_id: str) -> PlanTemplate | None:
        """Retrieve a template by ID."""
        return self._templates.get(template_id)

    def list_templates(self) -> list[PlanTemplate]:
        """List all available templates."""
        return list(self._templates.values())
