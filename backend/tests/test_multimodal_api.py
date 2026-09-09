"""Tests for Multimodal REST API Endpoints, Security, and Error States (Specs 78-80)."""

import base64
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app


@pytest.fixture
def app():
    return create_app()


@pytest.mark.asyncio
async def test_api_analyze_image_success(app):
    """POST /api/v1/multimodal/analyze successfully processes valid base64 image."""
    png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00 \x00\x00\x00 \x08\x06\x00\x00\x00"
    b64_img = base64.b64encode(png_bytes).decode("ascii")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/multimodal/analyze",
            headers={"x-user-id": "user_api_test"},
            json={
                "prompt": "What does this image show?",
                "attachments": [
                    {
                        "type": "image",
                        "mime_type": "image/png",
                        "filename": "screenshot.png",
                        "data_base64": b64_img,
                    }
                ],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "COMPLETED"
        assert len(data["evidence"]) >= 1
        assert "screenshot.png" in data["sources"][0]
        assert data["request_id"].startswith("req_")


@pytest.mark.asyncio
async def test_api_screen_capture_requires_device_id(app):
    """POST /api/v1/multimodal/analyze rejects capture_screen without device_id (Spec 48)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/multimodal/analyze",
            headers={"x-user-id": "user_api_test"},
            json={
                "prompt": "What is on my screen?",
                "capture_screen": True,
                "device_id": None,
            },
        )
        assert resp.status_code == 400
        assert "no bound 'device_id'" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_api_transcribe_audio_success(app):
    """POST /api/v1/multimodal/transcribe processes base64 audio with timestamps (Spec 79)."""
    wav_bytes = b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00"
    b64_audio = base64.b64encode(wav_bytes).decode("ascii")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/multimodal/transcribe",
            headers={"x-user-id": "user_api_test"},
            json={
                "audio_format": "wav",
                "audio_base64": b64_audio,
                "duration_seconds": 15.0,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "COMPLETED"
        assert len(data["evidence"]) > 0


@pytest.mark.asyncio
async def test_api_get_multimodal_request(app):
    """GET /api/v1/multimodal/{request_id} retrieves cached result or returns 404 (Spec 79)."""
    png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00 \x00\x00\x00 \x08\x06\x00\x00\x00"
    b64_img = base64.b64encode(png_bytes).decode("ascii")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create request first
        post_resp = await client.post(
            "/api/v1/multimodal/analyze",
            headers={"x-user-id": "user_api_test"},
            json={
                "prompt": "Inspect",
                "attachments": [{"type": "image", "data_base64": b64_img, "filename": "test.png"}],
            },
        )
        req_id = post_resp.json()["request_id"]

        # Fetch by ID
        get_resp = await client.get(
            f"/api/v1/multimodal/{req_id}",
            headers={"x-user-id": "user_api_test"},
        )
        assert get_resp.status_code == 200
        assert get_resp.json()["request_id"] == req_id

        # Missing ID returns 404
        missing_resp = await client.get(
            "/api/v1/multimodal/nonexistent_req_id",
            headers={"x-user-id": "user_api_test"},
        )
        assert missing_resp.status_code == 404
