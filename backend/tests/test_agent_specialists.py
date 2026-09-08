"""Unit tests for individual specialist agents (Researcher, Developer, Analyst, Browser)."""

from unittest.mock import AsyncMock

import pytest

from app.agents.schemas import AgentContext, AgentEvidence, AgentResult
from app.agents.specialists.analyst import AnalystSpecialist
from app.agents.specialists.browser import BrowserSpecialist
from app.agents.specialists.developer import DeveloperSpecialist
from app.agents.specialists.researcher import ResearcherSpecialist
from app.agents.state import AgentTaskStatus, AgentType, EvidenceType
from app.tools.schemas import ToolResult


@pytest.mark.asyncio
async def test_researcher_specialist_gathers_citations():
    """Researcher agent executes web_search and produces OBSERVED evidence and citations."""
    mock_executor = AsyncMock()
    mock_executor.execute.return_value = ToolResult(
        success=True,
        tool_name="web_search",
        tool_call_id="call_1",
        result={
            "results": [
                {
                    "title": "Python 3.13 Release Notes",
                    "url": "https://docs.python.org/3.13/",
                    "snippet": "Python 3.13 is now available with free-threaded mode.",
                }
            ]
        },
        verification_status="verified",
    )

    context = AgentContext(
        task_id="t_res",
        agent_type=AgentType.RESEARCHER,
        bounded_input="Research latest Python release",
        allowed_tools=["web_search", "web_fetch"],
    )

    result = await ResearcherSpecialist.run(context=context, tool_executor=mock_executor)

    assert result.status == AgentTaskStatus.COMPLETED
    assert len(result.citations) == 1
    assert result.citations[0].url == "https://docs.python.org/3.13/"
    assert len(result.evidence) >= 1
    assert result.evidence[0].type == EvidenceType.OBSERVED
    assert result.tool_calls_count == 1


@pytest.mark.asyncio
async def test_developer_specialist_inspects_repository():
    """Developer agent executes git_status and records repository evidence."""
    mock_executor = AsyncMock()
    mock_executor.execute.return_value = ToolResult(
        success=True,
        tool_name="git_status",
        tool_call_id="call_2",
        result={"is_clean": True, "branch": "main", "changed_files": []},
        verification_status="verified",
    )

    context = AgentContext(
        task_id="t_dev",
        agent_type=AgentType.DEVELOPER,
        bounded_input="Inspect repository git status and version",
        allowed_tools=["git_status", "code_search"],
    )

    result = await DeveloperSpecialist.run(context=context, tool_executor=mock_executor)

    assert result.status == AgentTaskStatus.COMPLETED
    assert any("main" in e.statement for e in result.evidence)
    assert any(e.type == EvidenceType.OBSERVED for e in result.evidence)


@pytest.mark.asyncio
async def test_analyst_specialist_synthesizes_without_tools():
    """Analyst operates without tools, compares upstream findings, and separates OBSERVED vs INFERRED."""
    res_result = AgentResult(
        task_id="t_res",
        agent_type=str(AgentType.RESEARCHER),
        summary="Python 3.13 is released.",
        evidence=[
            AgentEvidence(
                type=EvidenceType.OBSERVED,
                statement="Python 3.13 released October 2024",
                source="https://python.org",
            )
        ],
    )
    dev_result = AgentResult(
        task_id="t_dev",
        agent_type=str(AgentType.DEVELOPER),
        summary="Repository pins Python 3.11 in pyproject.toml.",
        evidence=[
            AgentEvidence(
                type=EvidenceType.OBSERVED,
                statement="Repository pins Python 3.11",
                source="pyproject.toml",
            )
        ],
    )

    context = AgentContext(
        task_id="t_ana",
        agent_type=AgentType.ANALYST,
        bounded_input="Compare compatibility for upgrade",
        dependencies_results={"t_res": res_result, "t_dev": dev_result},
        allowed_tools=[],
    )

    result = await AnalystSpecialist.run(context=context, tool_executor=None)

    assert result.status == AgentTaskStatus.COMPLETED
    assert result.tool_calls_count == 0

    # Must classify observed facts from upstream and infer deductions
    types = {e.type for e in result.evidence}
    assert EvidenceType.OBSERVED in types
    assert EvidenceType.INFERRED in types
    assert EvidenceType.UNKNOWN in types


@pytest.mark.asyncio
async def test_browser_specialist_inspects_page():
    """Browser specialist executes browser_inspect and records visual evidence."""
    mock_executor = AsyncMock()
    mock_executor.execute.return_value = ToolResult(
        success=True,
        tool_name="browser_inspect",
        tool_call_id="call_3",
        result={"url": "https://example.com", "title": "Example Domain"},
        verification_status="verified",
    )

    context = AgentContext(
        task_id="t_browser",
        agent_type=AgentType.BROWSER,
        bounded_input="Inspect page https://example.com",
        allowed_tools=["browser_inspect"],
    )

    result = await BrowserSpecialist.run(context=context, tool_executor=mock_executor)

    assert result.status == AgentTaskStatus.COMPLETED
    assert any("Example Domain" in e.statement for e in result.evidence)
