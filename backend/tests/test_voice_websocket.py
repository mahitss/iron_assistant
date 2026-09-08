"""Integration tests for Voice WebSocket protocol and real-time event exchange."""

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.voice.providers.mock import MockSTTProvider, MockTTSProvider
from app.voice.service import VoiceService


def _create_mock_app(voice_enabled: bool = True):
    """Create test FastAPI application with mocked STT and TTS providers."""
    from app.agents.core import KairoAgent
    from app.api.routes import voice
    from app.models.provider import ModelProvider, ProviderResponse

    class SimpleMockProvider(ModelProvider):
        async def generate_response(self, messages, model=None, stream=False, tools=None):
            return ProviderResponse(content="I am Kairo, your personal assistant.", model="mock-model")

        async def stream_response(self, messages, model=None, tools=None):
            yield "I am Kairo, "
            yield "your personal assistant."

    agent = KairoAgent(
        provider=SimpleMockProvider(),
        memory_extraction_enabled=False,
    )

    settings = Settings(
        KAIRO_VOICE_ENABLED=voice_enabled,
        KAIRO_VOICE_SAMPLE_RATE=16000,
        KAIRO_VOICE_MAX_SESSION_SECONDS=600,
        KAIRO_VOICE_MAX_AUDIO_CHUNK_BYTES=65536,
    )

    stt = MockSTTProvider(default_text="Hello Kairo assistant")
    tts = MockTTSProvider()
    service = VoiceService(agent=agent, stt_provider=stt, tts_provider=tts, settings=settings)

    # Inject service into voice route module
    voice._GLOBAL_VOICE_SERVICE = service

    return create_app()


def test_websocket_start_and_end_session():
    """Verify client can connect, send start_session, and cleanly end session."""
    app = _create_mock_app(voice_enabled=True)
    client = TestClient(app)

    with client.websocket_connect("/api/v1/voice") as ws:
        ws.send_json({"type": "start_session", "sample_rate": 16000})
        start_event = ws.receive_json()
        assert start_event["type"] == "session_started"
        assert "session_id" in start_event

        # End session
        ws.send_json({"type": "end_session"})
        end_event = ws.receive_json()
        assert end_event["type"] == "session_ended"


def test_websocket_audio_chunk_and_response_flow():
    """Verify audio chunk sent over WebSocket triggers transcription, reasoning, and response."""
    app = _create_mock_app(voice_enabled=True)
    client = TestClient(app)

    with client.websocket_connect("/api/v1/voice") as ws:
        ws.send_json({"type": "start_session", "session_id": "ws_flow_1"})
        start_event = ws.receive_json()
        assert start_event["type"] == "session_started"

        # Send audio chunk (over 1000 bytes) and trigger stop_speaking
        mock_audio = b"\x00\x01" * 800  # 1600 bytes
        ws.send_bytes(mock_audio)
        ws.send_json({"type": "stop_speaking"})

        # Collect server events
        events_received = []
        audio_received = []

        for _ in range(10):
            msg = ws.receive()
            if "text" in msg and msg["text"]:
                import json
                data = json.loads(msg["text"])
                events_received.append(data["type"])
                if data["type"] == "response_complete":
                    break
            elif "bytes" in msg and msg["bytes"]:
                audio_received.append(msg["bytes"])

        assert "transcript_final" in events_received
        assert "thinking" in events_received
        assert "response_text" in events_received
        assert "response_complete" in events_received
        assert len(audio_received) > 0


def test_websocket_interrupt_handling():
    """Verify client sending interrupt receives interrupted acknowledgment."""
    app = _create_mock_app(voice_enabled=True)
    client = TestClient(app)

    with client.websocket_connect("/api/v1/voice") as ws:
        ws.send_json({"type": "start_session", "session_id": "ws_int_1"})
        ws.receive_json()

        # Send interrupt
        ws.send_json({"type": "interrupt"})
        int_event = ws.receive_json()
        assert int_event["type"] == "interrupted"


def test_websocket_malformed_json_error():
    """Verify sending malformed text frame returns MALFORMED_JSON error."""
    app = _create_mock_app(voice_enabled=True)
    client = TestClient(app)

    with client.websocket_connect("/api/v1/voice") as ws:
        ws.send_text("this is not valid json")
        err = ws.receive_json()
        assert err["type"] == "error"
        assert err["code"] == "MALFORMED_JSON"


def test_websocket_voice_disabled():
    """Verify connecting when voice is disabled returns error and closes connection."""
    from starlette.websockets import WebSocketDisconnect

    app = _create_mock_app(voice_enabled=False)
    client = TestClient(app)

    with client.websocket_connect("/api/v1/voice") as ws:
        err = ws.receive_json()
        assert err["type"] == "error"
        assert err["code"] == "VOICE_DISABLED"
        with pytest.raises(WebSocketDisconnect):
            ws.receive_json()

