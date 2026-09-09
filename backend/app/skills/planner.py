"""Bounded plan generator for executable skills."""

import logging
import uuid
from typing import Any

from app.config.settings import get_settings
from app.skills.schemas import SkillManifest, SkillPlan, SkillPlanStep, SkillRiskLevel

logger = logging.getLogger("kairo.skills.planner")


class SkillPlanner:
    """Constructs structured, sequential execution plans for resolved skills."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.max_steps = self.settings.KAIRO_MAX_SKILL_STEPS

    def create_plan(
        self,
        manifest: SkillManifest,
        inputs: dict[str, Any],
        goal: str | None = None,
    ) -> SkillPlan:
        """Construct a bounded SkillPlan tailored to the skill's manifest and input parameters."""
        plan_id = f"plan_{uuid.uuid4().hex[:12]}"
        plan_goal = goal or f"Execute skill '{manifest.name}' ({manifest.id})"
        steps: list[SkillPlanStep] = []

        # Built-in plan recipes based on skill ID
        if manifest.id == "research.web":
            query = inputs.get("query", "")
            steps.append(
                SkillPlanStep(
                    step_number=1,
                    description=f"Perform web search for: '{query[:60]}'",
                    tool_name="web_search",
                    arguments={"query": query, "num_results": inputs.get("max_results", 5)},
                    risk_level=SkillRiskLevel.READ_ONLY,
                )
            )
            if "web_fetch" in manifest.optional_tools:
                steps.append(
                    SkillPlanStep(
                        step_number=2,
                        description="Fetch and extract detailed content from top relevant source URL",
                        tool_name="web_fetch",
                        arguments={"url": inputs.get("url", "")},
                        risk_level=SkillRiskLevel.READ_ONLY,
                    )
                )

        elif manifest.id == "developer.repository":
            action = inputs.get("action", "status")
            if action in ("status", "inspect"):
                steps.append(
                    SkillPlanStep(
                        step_number=1,
                        description="Inspect repository status and current branch state",
                        tool_name="git_status",
                        arguments={},
                        risk_level=SkillRiskLevel.READ_ONLY,
                    )
                )
                steps.append(
                    SkillPlanStep(
                        step_number=2,
                        description="Inspect recent working tree diffs",
                        tool_name="git_diff",
                        arguments={},
                        risk_level=SkillRiskLevel.READ_ONLY,
                    )
                )
            elif action == "analyze":
                steps.append(
                    SkillPlanStep(
                        step_number=1,
                        description=f"Run static code analysis on target path: {inputs.get('path', '.')}",
                        tool_name="code_analyze",
                        arguments={"path": inputs.get("path", ".")},
                        risk_level=SkillRiskLevel.READ_ONLY,
                    )
                )

        elif manifest.id == "github.analysis":
            repo = inputs.get("repository", "")
            steps.append(
                SkillPlanStep(
                    step_number=1,
                    description=f"Inspect GitHub repository metadata for: {repo}",
                    tool_name="github_get_repository",
                    arguments={"repo_name": repo},
                    risk_level=SkillRiskLevel.READ_ONLY,
                )
            )
            if inputs.get("pr_number"):
                steps.append(
                    SkillPlanStep(
                        step_number=2,
                        description=f"Inspect Pull Request #{inputs['pr_number']}",
                        tool_name="github_get_pull_request",
                        arguments={"repo_name": repo, "pr_number": inputs["pr_number"]},
                        risk_level=SkillRiskLevel.READ_ONLY,
                    )
                )
            elif inputs.get("issue_number"):
                steps.append(
                    SkillPlanStep(
                        step_number=2,
                        description=f"Inspect Issue #{inputs['issue_number']}",
                        tool_name="github_get_issue",
                        arguments={"repo_name": repo, "issue_number": inputs["issue_number"]},
                        risk_level=SkillRiskLevel.READ_ONLY,
                    )
                )
            else:
                steps.append(
                    SkillPlanStep(
                        step_number=2,
                        description=f"Inspect CI status checks for: {repo}",
                        tool_name="github_get_checks",
                        arguments={"repo_name": repo},
                        risk_level=SkillRiskLevel.READ_ONLY,
                    )
                )

        elif manifest.id == "browser.research":
            url = inputs.get("url", "https://kairo.ai")
            steps.append(
                SkillPlanStep(
                    step_number=1,
                    description=f"Navigate browser to URL: {url}",
                    tool_name="browser_navigate",
                    arguments={"url": url},
                    risk_level=SkillRiskLevel.LOW,
                )
            )
            steps.append(
                SkillPlanStep(
                    step_number=2,
                    description="Inspect page structure and extract DOM content",
                    tool_name="browser_inspect",
                    arguments={},
                    risk_level=SkillRiskLevel.LOW,
                )
            )

        elif manifest.id == "computer.assist":
            action = inputs.get("action", "screenshot")
            if action == "screenshot":
                steps.append(
                    SkillPlanStep(
                        step_number=1,
                        description="Capture authorized desktop screenshot via Local Companion",
                        tool_name="computer_screenshot",
                        arguments={},
                        risk_level=SkillRiskLevel.LOW,
                    )
                )
            elif action == "click":
                steps.append(
                    SkillPlanStep(
                        step_number=1,
                        description=f"Click coordinates ({inputs.get('x', 0)}, {inputs.get('y', 0)})",
                        tool_name="computer_click",
                        arguments={"x": inputs.get("x", 0), "y": inputs.get("y", 0)},
                        risk_level=SkillRiskLevel.HIGH,
                    )
                )
            elif action == "type":
                steps.append(
                    SkillPlanStep(
                        step_number=1,
                        description="Type text input on authorized desktop",
                        tool_name="computer_type",
                        arguments={"text": inputs.get("text", "")},
                        risk_level=SkillRiskLevel.HIGH,
                    )
                )

        # Generic default plan using required tools
        if not steps:
            for idx, tool in enumerate(manifest.required_tools[: self.max_steps]):
                steps.append(
                    SkillPlanStep(
                        step_number=idx + 1,
                        description=f"Execute required tool: '{tool}'",
                        tool_name=tool,
                        arguments=inputs,
                        risk_level=manifest.risk_level,
                    )
                )

        # Enforce step limit bounding
        bounded_steps = steps[: min(len(steps), self.max_steps, manifest.execution_limits.max_steps)]

        plan = SkillPlan(
            plan_id=plan_id,
            skill_id=manifest.id,
            goal=plan_goal,
            steps=bounded_steps,
        )
        logger.info(
            "Generated plan '%s' with %d steps for skill '%s'", plan.plan_id, len(plan.steps), manifest.id
        )
        return plan
