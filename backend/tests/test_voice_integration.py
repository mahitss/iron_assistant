"""Integration tests for Voice system with Kairo Core reasoning, tools, and memory."""


import pytest

from app.agents.core import KairoAgent
from app.models.provider import ModelProvider, ProviderResponse, ToolCall
from app.tools.builtin.calculator import CalculatorTool
from app.tools.executor import ToolExecutor
from app.tools.registry import ToolRegistry
from app.voice.providers.mock import MockSTTProvider, MockTTSProvider
from app.voice.service import VoiceService


class MockToolModelProvider(ModelProvider):
    """Model provider returning a tool call followed by final answer."""

    def __init__(self):
        self.step = 0

    async def generate_response(self, messages, model=None, stream=False, tools=None):
        if self.step == 0:
            self.step += 1
            return ProviderResponse(
                content=None,
                model="test-model",
                tool_calls=[
                    ToolCall(
                        id="call_calc_1",
                        name="calculator",
                        arguments={"expression": "12 * 12"},
                    )
                ],
            )
        return ProviderResponse(
            content="12 times 12 is 144.",
            model="test-model",
        )

    async def stream_response(self, messages, model=None, tools=None):
        yield "12 times 12 is 144."


@pytest.mark.asyncio
async def test_voice_end_to_end_with_tool_execution():
    """Verify speech input executes Kairo tools and returns synthesized spoken answer."""
    registry = ToolRegistry()
    registry.register(CalculatorTool())
    executor = ToolExecutor(registry=registry)

    provider = MockToolModelProvider()
    agent = KairoAgent(
        provider=provider,
        tool_registry=registry,
        tool_executor=executor,
        memory_extraction_enabled=False,
    )

    stt = MockSTTProvider(default_text="What is 12 times 12?")
    tts = MockTTSProvider()

    service = VoiceService(
        agent=agent,
        stt_provider=stt,
        tts_provider=tts,
    )

    session = await service.create_session("voice_integ_sess")

    events = []
    audio_chunks = []

    async def mock_emit_event(event):
        events.append(event)

    async def mock_emit_audio(chunk):
        audio_chunks.append(chunk)

    # Send 1600 bytes of audio and force process
    await service.handle_audio_chunk(
        session=session,
        chunk=b"\x01\x02" * 800,
        emit_event=mock_emit_event,
        emit_audio=mock_emit_audio,
    )
    await service.force_process_speech(
        session=session,
        emit_event=mock_emit_event,
        emit_audio=mock_emit_audio,
    )

    # 1. Verify transcription
    event_types = [e["type"] for e in events]
    assert "transcript_final" in event_types
    assert "thinking" in event_types
    assert "tool_activity" in event_types
    assert "response_text" in event_types
    assert "response_complete" in event_types

    # 2. Verify tool activity metadata is safe
    tool_events = [e for e in events if e["type"] == "tool_activity"]
    assert len(tool_events) >= 1
    assert tool_events[0]["tool"] == "calculator"
    assert tool_events[0]["status"] == "success"

    # 3. Verify audio synthesis received complete answer
    assert "12 times 12 is 144." in tts.synthesized_texts
    assert len(audio_chunks) > 0

    # 4. Privacy verification: Audio buffer cleared
    assert session.get_audio_bytes() == b""

    await service.close_session("voice_integ_sess")
