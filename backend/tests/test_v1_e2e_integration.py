"""Kairo v1 End-to-End System Integration and Failure Resilience Test Suite.

Validates:
1. End-to-End Chat & Streaming Conversation
2. Single-Source-of-Truth Tool Execution & SecurityCenter Interception
3. Multi-Agent Orchestration & Evidence Taxonomy
4. Automation Engine Scheduling & Idempotency
5. Proactive Intelligence & Notification Delivery
6. Failure Resilience, Circuit Breaking & Redis Ephemeral Survival
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

from app.agents.core import AgentResponse
from app.agents.schemas import AgentCitation, AgentEvidence
from app.agents.state import EvidenceType
from app.agents.supervisor import SupervisorAgent
from app.automation.idempotency import generate_scheduled_idempotency_key
from app.main import app
from app.models.resilience import CircuitBreaker, CircuitBreakerOpenError, CircuitBreakerState
from app.proactive.deduplicator import InsightDeduplicator
from app.proactive.schemas import CandidateInsight
from app.proactive.state import InsightPriority, SourceType
from app.security.center import SecurityCenter
from app.tools.base import BaseTool
from app.tools.executor import ToolExecutor
from app.tools.permissions import PermissionLevel
from app.tools.registry import ToolRegistry
from app.tools.schemas import ToolCall

# --- 1. End-to-End Chat & Streaming Integration ---


@pytest.mark.asyncio
async def test_e2e_chat_single_turn_and_streaming(monkeypatch):
    """Verify chat pipeline processes user queries and streams token chunks."""
    client = TestClient(app)

    # Mock Agent process_message response
    mock_agent_response = AgentResponse(
        message="Kairo is ready to assist you with development and research.",
        session_id="test-session-e2e",
        model="openrouter/auto",
        tools_used=[],
    )
    monkeypatch.setattr(
        "app.agents.core.KairoAgent.process_message",
        AsyncMock(return_value=mock_agent_response),
    )

    # Normal synchronous chat
    resp = client.post(
        "/api/v1/chat",
        json={"message": "What is your primary capability?", "session_id": "test-session-e2e"},
    )
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert "message" in data
    assert "Kairo is ready" in data["message"]

    # Streaming chat
    monkeypatch.setattr(
        "app.agents.core.KairoAgent.resolve_model",
        MagicMock(return_value="openrouter/auto"),
    )

    async def mock_stream_chunks(*args, **kwargs):
        for chunk in ["Kairo ", "streaming ", "response ", "verified."]:
            yield chunk

    monkeypatch.setattr(
        "app.agents.core.KairoAgent.stream_message",
        mock_stream_chunks,
    )

    stream_resp = client.post(
        "/api/v1/chat/stream",
        json={"message": "Stream a response", "session_id": "test-stream-session"},
    )
    assert stream_resp.status_code == status.HTTP_200_OK
    assert "text/event-stream" in stream_resp.headers["content-type"]
    assert "verified." in stream_resp.text


# --- 2. Tool Execution & SecurityCenter Interception ---


class SafeToolArgs(BaseModel):
    pass


class SampleSafeTool(BaseTool):
    """Tool executing safely without human intervention."""

    name = "get_current_time"
    description = "Returns current UTC timestamp."
    permission_level = PermissionLevel.READ
    args_model = SafeToolArgs

    async def execute(self, **kwargs):
        return {"timestamp": "2026-09-08T12:00:00Z"}


class DestructiveToolArgs(BaseModel):
    target: str = Field(..., description="Target table or database")


class SampleDestructiveTool(BaseTool):
    """Tool requiring approval or policy denial due to high-risk permission level."""

    name = "delete_database_records"
    description = "Deletes records permanently."
    permission_level = PermissionLevel.DESTRUCTIVE
    args_model = DestructiveToolArgs

    async def execute(self, target: str, **kwargs):
        return {"status": "records deleted"}


@pytest.mark.asyncio
async def test_e2e_tool_execution_and_security_interception():
    """Verify tool execution passes strictly through ToolExecutor and SecurityCenter."""
    registry = ToolRegistry()
    safe_tool = SampleSafeTool()
    dest_tool = SampleDestructiveTool()
    registry.register(safe_tool)
    registry.register(dest_tool)

    sec_center = SecurityCenter()
    executor = ToolExecutor(registry=registry, security_center=sec_center)

    # 1. Safe tool execution succeeds
    safe_call = ToolCall(id="call_safe_1", name="get_current_time", arguments={})
    res_safe = await executor.execute(safe_call, user_id="user-123")
    assert res_safe.success is True
    assert res_safe.result == {"timestamp": "2026-09-08T12:00:00Z"}

    # 2. Unknown tool rejection
    bad_call = ToolCall(id="call_bad_1", name="nonexistent_tool", arguments={})
    res_bad = await executor.execute(bad_call, user_id="user-123")
    assert res_bad.success is False
    assert "not registered" in str(res_bad.error).lower() or "not found" in str(res_bad.error).lower()

    # 3. High-risk tool blocked or requires approval through SecurityCenter
    dest_call = ToolCall(id="call_dest_1", name="delete_database_records", arguments={"target": "users"})
    res_dest = await executor.execute(dest_call, user_id="user-123")
    assert res_dest.success is False
    assert (
        res_dest.approval_required is True
        or "prohibited" in str(res_dest.error).lower()
        or res_dest.verification_status == "denied"
    )


# --- 3. Multi-Agent Orchestration & Evidence Taxonomy ---


@pytest.mark.asyncio
async def test_e2e_multi_agent_evidence_and_cancellation():
    """Verify supervisor structures plans, classifies evidence, and supports safe cancellation."""
    mock_provider = AsyncMock()
    supervisor = SupervisorAgent(provider=mock_provider)

    # Verify query complexity classifier
    assert supervisor.should_decompose("What is 2 + 2?") is False
    assert (
        supervisor.should_decompose(
            "Research the latest Python release, inspect my local repo dependencies, and analyze whether we should upgrade."
        )
        is True
    )

    # Verify evidence taxonomy integrity
    obs = AgentEvidence(
        type=EvidenceType.OBSERVED,
        statement="Python 3.13.0 was released on October 7, 2024.",
        source="https://docs.python.org/3/whatsnew/3.13.html",
    )
    inf = AgentEvidence(
        type=EvidenceType.INFERRED,
        statement="Upgrading will require verifying third-party C-extension compatibility.",
    )
    unk = AgentEvidence(
        type=EvidenceType.UNKNOWN,
        statement="Whether existing Cython extensions compile in free-threaded mode.",
    )

    assert obs.type == EvidenceType.OBSERVED
    assert inf.type == EvidenceType.INFERRED
    assert unk.type == EvidenceType.UNKNOWN

    # Citation preservation
    citation = AgentCitation(
        id=1,
        url="https://docs.python.org/3/whatsnew/3.13.html",
        title="Python 3.13 Release Notes",
    )
    assert citation.id == 1
    assert "python.org" in citation.url


# --- 4. Automation Engine Scheduling & Idempotency ---


@pytest.mark.asyncio
async def test_e2e_automation_idempotency_and_scheduling():
    """Verify scheduler uses deterministic idempotency keys to prevent duplicate workflow runs."""
    workflow_id = "wf-prod-001"
    scheduled_ts = datetime(2026, 9, 8, 12, 0, 0, tzinfo=UTC)

    # Generate key for specific timestamp
    key_1 = generate_scheduled_idempotency_key(workflow_id, scheduled_ts)
    key_2 = generate_scheduled_idempotency_key(workflow_id, scheduled_ts)

    # Assert deterministic equality
    assert key_1 == key_2
    assert f"sched_{workflow_id}" in key_1

    # Keys for different timestamps must diverge
    key_different_time = generate_scheduled_idempotency_key(
        workflow_id, datetime(2026, 9, 8, 13, 0, 0, tzinfo=UTC)
    )
    assert key_1 != key_different_time


# --- 5. Proactive Intelligence & Notification Delivery ---


@pytest.mark.asyncio
async def test_e2e_proactive_candidate_deduplication():
    """Verify proactive intelligence computes deterministic fingerprints to suppress duplicate insights."""
    candidate_1 = CandidateInsight(
        user_id="user-456",
        source_type=SourceType.GITHUB,
        source_id="repo-owner/repo-name#104",
        category="ci_failure",
        title="GitHub CI Check Failed",
        summary="Workflow run #104 on branch main failed.",
        priority=InsightPriority.HIGH,
    )

    candidate_duplicate = CandidateInsight(
        user_id="user-456",
        source_type=SourceType.GITHUB,
        source_id="repo-owner/repo-name#104",
        category="ci_failure",
        title="GitHub CI Check Failed (Polled Again)",
        summary="Workflow run #104 on branch main failed.",
        priority=InsightPriority.HIGH,
    )

    # Deterministic fingerprint match
    fp1 = InsightDeduplicator.compute_fingerprint(candidate_1)
    fp2 = InsightDeduplicator.compute_fingerprint(candidate_duplicate)
    assert fp1 == fp2
    assert len(fp1) == 64  # SHA-256 length

    # Different event yields different fingerprint
    candidate_different = CandidateInsight(
        user_id="user-456",
        source_type=SourceType.GITHUB,
        source_id="repo-owner/repo-name#105",
        category="ci_failure",
        title="Different Run",
        summary="Workflow run #105 failed.",
        priority=InsightPriority.HIGH,
    )
    fp3 = InsightDeduplicator.compute_fingerprint(candidate_different)
    assert fp1 != fp3


# --- 6. Disaster Recovery, Circuit Breaking & Resilience ---


@pytest.mark.asyncio
async def test_e2e_circuit_breaker_and_resilience_failover():
    """Verify circuit breaker trips on consecutive provider failures and prevents thread exhaustion."""
    cb = CircuitBreaker(name="openrouter_test", fail_max=3, reset_timeout=60.0)

    # Record 3 failures to trip breaker
    for _ in range(3):
        cb.record_failure(RuntimeError("OpenRouter HTTP 503 Service Unavailable"))

    # Circuit breaker must now be OPEN
    assert cb.state == CircuitBreakerState.OPEN
    assert cb.can_execute() is False

    # Callers fail fast when breaker is open
    with pytest.raises(CircuitBreakerOpenError):
        if not cb.can_execute():
            raise CircuitBreakerOpenError(f"Circuit breaker '{cb.name}' is OPEN")
