"""Tests for the SupervisorAgent (planning, delegation, conflict synthesis, and citation preservation)."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.agents.schemas import AgentCitation, AgentEvidence, AgentPlan, AgentResult, AgentTaskSpec
from app.agents.state import AgentTaskStatus, AgentType, EvidenceType
from app.agents.supervisor import SupervisorAgent


@pytest.mark.asyncio
async def test_supervisor_should_decompose():
    """Simple questions do not decompose; multi-step cross-domain queries do decompose."""
    mock_provider = AsyncMock()
    supervisor = SupervisorAgent(provider=mock_provider)

    assert not supervisor.should_decompose("What is Python?")
    assert not supervisor.should_decompose("Hello Kairo")
    assert not supervisor.should_decompose("2 + 2")

    assert supervisor.should_decompose(
        "Research the latest Python release, inspect my Kairo repository, and tell me whether we should upgrade."
    )
    assert supervisor.should_decompose(
        "Investigate why CI is failing on GitHub and propose a fix from the code."
    )


@pytest.mark.asyncio
async def test_supervisor_deterministic_synthesis_preserves_evidence_taxonomy():
    """Supervisor groups evidence into OBSERVED, INFERRED, and UNKNOWN when synthesizing."""
    mock_provider = AsyncMock()
    supervisor = SupervisorAgent(provider=mock_provider)

    results = {
        "t1": AgentResult(
            task_id="t1",
            agent_type=str(AgentType.RESEARCHER),
            status=AgentTaskStatus.COMPLETED,
            summary="Python 3.13 is current.",
            evidence=[
                AgentEvidence(
                    type=EvidenceType.OBSERVED,
                    statement="Python 3.13 released October 2024",
                    source="https://docs.python.org/3.13/",
                )
            ],
            citations=[
                AgentCitation(
                    id=1,
                    title="Python 3.13 Docs",
                    url="https://docs.python.org/3.13/",
                )
            ],
        ),
        "t2": AgentResult(
            task_id="t2",
            agent_type=str(AgentType.DEVELOPER),
            status=AgentTaskStatus.COMPLETED,
            summary="Repository specifies Python 3.11.",
            evidence=[
                AgentEvidence(
                    type=EvidenceType.OBSERVED,
                    statement="Repository config pins Python 3.11",
                    source="pyproject.toml",
                )
            ],
        ),
        "t3": AgentResult(
            task_id="t3",
            agent_type=str(AgentType.ANALYST),
            status=AgentTaskStatus.COMPLETED,
            summary="Upgrade to 3.13 requires testing external dependencies.",
            evidence=[
                AgentEvidence(
                    type=EvidenceType.INFERRED,
                    statement="Upgrade requires testing dependencies for compatibility",
                ),
                AgentEvidence(
                    type=EvidenceType.UNKNOWN,
                    statement="Whether production dependencies support Python 3.13",
                ),
            ],
        ),
    }

    budget_tracker = MagicMock()
    response = await supervisor.synthesize_results(
        user_message="Should we upgrade Python?",
        results=results,
        budget_tracker=budget_tracker,
    )

    content = response.message
    assert "Observed Facts:" in content
    assert "Inferred Conclusions:" in content
    assert "Unresolved / Unknown:" in content
    assert "Python 3.13 released October 2024" in content
    assert "Repository config pins Python 3.11" in content


@pytest.mark.asyncio
async def test_supervisor_end_to_end_execution(monkeypatch):
    """Supervisor creates plan, delegates via executor, and synthesizes final answer."""
    mock_provider = AsyncMock()
    supervisor = SupervisorAgent(provider=mock_provider)

    # Mock planner.create_plan
    async def mock_create_plan(*args, **kwargs):
        return AgentPlan(
            tasks=[
                AgentTaskSpec(task_id="t_res", agent_type=AgentType.RESEARCHER, objective="Research release"),
                AgentTaskSpec(task_id="t_dev", agent_type=AgentType.DEVELOPER, objective="Inspect repo"),
                AgentTaskSpec(
                    task_id="t_ana",
                    agent_type=AgentType.ANALYST,
                    objective="Compare",
                    dependencies=["t_res", "t_dev"],
                ),
            ]
        )

    # Mock executor.execute_plan
    async def mock_execute_plan(*args, **kwargs):
        return {
            "t_res": AgentResult(
                task_id="t_res",
                agent_type=str(AgentType.RESEARCHER),
                status=AgentTaskStatus.COMPLETED,
                summary="Python 3.13 is current.",
            ),
            "t_dev": AgentResult(
                task_id="t_dev",
                agent_type=str(AgentType.DEVELOPER),
                status=AgentTaskStatus.COMPLETED,
                summary="Repo uses 3.11.",
            ),
            "t_ana": AgentResult(
                task_id="t_ana",
                agent_type=str(AgentType.ANALYST),
                status=AgentTaskStatus.COMPLETED,
                summary="Upgrade feasible after testing.",
            ),
        }

    monkeypatch.setattr(supervisor.planner, "create_plan", mock_create_plan)
    monkeypatch.setattr(supervisor.executor, "execute_plan", mock_execute_plan)

    events = []

    def event_cb(event_type, agent_type, task_id, message):
        events.append((event_type, agent_type, message))

    response = await supervisor.execute(
        message="Research python and check repo",
        user_id="u_1",
        session_id="s_1",
        event_callback=event_cb,
    )

    assert response.message
    assert any(evt[0] == "synthesis_started" for evt in events)
    assert "Python 3.13 is current" in response.message
    assert "Repo uses 3.11" in response.message
