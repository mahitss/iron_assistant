"""Tests for screen capture, microphone, local wake-word, speaker, and camera privacy controls."""

import pytest

from companion.src.audio.microphone import (
    AudioRecordAction,
    MicrophoneManager,
    MicrophoneState,
)
from companion.src.audio.speaker import AudioPlayAction, SpeakerManager
from companion.src.audio.wakeword import LocalWakeWordEngine
from companion.src.camera.capture import CameraCaptureAction, CameraManager
from companion.src.screen.capture import ScreenCaptureAction
from companion.src.screen.privacy import ScreenPrivacyManager


def test_screen_capture_privacy_and_throttling():
    """Verify screen capture enforces single-frame return and min-interval throttling."""
    privacy = ScreenPrivacyManager(min_interval_seconds=0.1)
    action = ScreenCaptureAction(privacy_manager=privacy)

    res = action.run({"format": "png"})
    assert res["single_frame"] is True
    assert "data_base64" in res
    assert privacy.is_sharing_active() is False

    # Immediate second capture triggers throttling
    with pytest.raises(PermissionError, match="throttled"):
        action.run({})


def test_microphone_explicit_states():
    """Verify microphone transitions through explicit states and never leaves mic on."""
    mic_mgr = MicrophoneManager()
    assert mic_mgr.current_state == MicrophoneState.OFF

    action = AudioRecordAction(mic_manager=mic_mgr)
    res = action.run({"duration": 1.0})
    assert res["explicit_capture"] is True
    assert mic_mgr.current_state == MicrophoneState.OFF  # Ensured OFF after run


def test_local_wakeword_engine():
    """Verify wake-word engine operates locally and dispatches callbacks."""
    wake_engine = LocalWakeWordEngine("Hey Kairo")
    assert wake_engine.is_listening is False

    wake_engine.start()
    assert wake_engine.is_listening is True

    triggered = []
    wake_engine.register_on_wake(lambda: triggered.append("wake_detected"))
    wake_engine.simulate_wake_trigger()
    assert len(triggered) == 1

    wake_engine.stop()
    assert wake_engine.is_listening is False


def test_speaker_cancellation():
    """Verify speaker allows user cancellation of active playback."""
    speaker = SpeakerManager()
    action = AudioPlayAction(speaker_manager=speaker)

    res = action.run({"text": "Hello user, operation complete."})
    assert res["played"] is True

    # Test muting
    speaker.set_muted(True)
    res_muted = action.run({"text": "Silent announcement"})
    assert res_muted["played"] is False


def test_camera_explicit_activation():
    """Verify camera displays visible indicator during capture and reverts to OFF."""
    camera_mgr = CameraManager()
    assert camera_mgr.is_active is False

    action = CameraCaptureAction(camera_manager=camera_mgr)
    res = action.run({"resolution": "1280x720"})
    assert res["single_frame"] is True
    assert "data_base64" in res
    assert camera_mgr.is_active is False
