"""WebSocket endpoint for real-time Kairo voice communication."""

import base64
import json
import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.agents.core import KairoAgent, get_default_agent
from app.voice.service import VoiceService

logger = logging.getLogger("kairo.voice.ws")

router = APIRouter(tags=["Voice"])

_GLOBAL_VOICE_SERVICE: VoiceService | None = None


def get_voice_service(agent: KairoAgent | None = None) -> VoiceService:
    """Provide singleton or configured VoiceService instance."""
    global _GLOBAL_VOICE_SERVICE
    if _GLOBAL_VOICE_SERVICE is None:
        ag = agent or get_default_agent()
        _GLOBAL_VOICE_SERVICE = VoiceService(agent=ag)
    return _GLOBAL_VOICE_SERVICE


@router.websocket("/voice")
async def websocket_voice_endpoint(websocket: WebSocket) -> None:
    """Full-duplex WebSocket endpoint for real-time voice streaming.

    Protocol:
    - Text frames: JSON metadata and control events (start_session, stop_speaking, interrupt, end_session).
    - Binary frames: 16kHz linear PCM audio chunks in both directions.
    """
    await websocket.accept()

    service = get_voice_service()
    if not service.settings.KAIRO_VOICE_ENABLED:
        await websocket.send_json({
            "type": "error",
            "message": "Voice system is currently disabled by configuration.",
            "code": "VOICE_DISABLED",
        })
        await websocket.close(code=1008)
        return
    session = None

    async def emit_event(event_dict: dict[str, Any]) -> None:
        try:
            await websocket.send_json(event_dict)
        except Exception as exc:
            logger.debug("Failed to send WebSocket event: %s", exc)

    async def emit_audio(audio_chunk: bytes) -> None:
        try:
            await websocket.send_bytes(audio_chunk)
        except Exception as exc:
            logger.debug("Failed to send WebSocket audio frame: %s", exc)

    try:
        while True:
            msg = await websocket.receive()
            msg_type = msg.get("type")

            if msg_type == "websocket.disconnect":
                break

            # 1. Binary Audio Frame received from client
            if "bytes" in msg and msg["bytes"] is not None:
                audio_bytes = msg["bytes"]
                if session is None:
                    session = await service.create_session()
                    await emit_event({
                        "type": "session_started",
                        "session_id": session.session_id,
                        "sample_rate": session.sample_rate,
                    })

                await service.handle_audio_chunk(
                    session=session,
                    chunk=audio_bytes,
                    emit_event=emit_event,
                    emit_audio=emit_audio,
                )

            # 2. Text Event Frame received from client
            elif "text" in msg and msg["text"] is not None:
                text_content = msg["text"].strip()
                if not text_content:
                    continue

                try:
                    payload = json.loads(text_content)
                except json.JSONDecodeError:
                    await emit_event({
                        "type": "error",
                        "message": "Invalid JSON format in control frame.",
                        "code": "MALFORMED_JSON",
                    })
                    continue

                event_type = payload.get("type")

                if event_type == "start_session":
                    requested_sid = payload.get("session_id")
                    session = await service.create_session(session_id=requested_sid)
                    await emit_event({
                        "type": "session_started",
                        "session_id": session.session_id,
                        "sample_rate": session.sample_rate,
                    })

                elif event_type == "audio_chunk":
                    # Fallback text-based audio chunk
                    b64_data = payload.get("data", "")
                    try:
                        chunk = base64.b64decode(b64_data)
                    except Exception:
                        await emit_event({
                            "type": "error",
                            "message": "Malformed base64 audio chunk.",
                            "code": "INVALID_AUDIO",
                        })
                        continue

                    if session is None:
                        session = await service.create_session()
                        await emit_event({
                            "type": "session_started",
                            "session_id": session.session_id,
                            "sample_rate": session.sample_rate,
                        })

                    await service.handle_audio_chunk(
                        session=session,
                        chunk=chunk,
                        emit_event=emit_event,
                        emit_audio=emit_audio,
                    )

                elif event_type == "stop_speaking":
                    if session:
                        await service.force_process_speech(
                            session=session,
                            emit_event=emit_event,
                            emit_audio=emit_audio,
                        )

                elif event_type == "interrupt":
                    if session:
                        await service.handle_interrupt(session=session, emit_event=emit_event)

                elif event_type == "end_session":
                    if session:
                        sid = session.session_id
                        await service.close_session(sid)
                        await emit_event({"type": "session_ended", "session_id": sid})
                        session = None
                    break

                else:
                    await emit_event({
                        "type": "error",
                        "message": f"Unrecognized client event type: '{event_type}'",
                        "code": "UNKNOWN_EVENT",
                    })

    except WebSocketDisconnect:
        logger.info("Client disconnected from voice session.")
    except Exception as exc:
        logger.error("Unexpected error in voice WebSocket connection: %s", exc, exc_info=True)
        try:
            await emit_event({
                "type": "error",
                "message": f"Internal server error: {exc}",
                "code": "SERVER_ERROR",
            })
        except Exception:
            pass
    finally:
        if session:
            await service.close_session(session.session_id)
