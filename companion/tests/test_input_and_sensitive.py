"""Tests for mouse bounds, keyboard actions, and sensitive field protection."""

import pytest

from companion.src.input.keyboard import KeyboardAction
from companion.src.input.mouse import MouseAction
from companion.src.input.sensitive import SensitiveContextDetector


def test_mouse_coordinate_bounds_and_buttons():
    """Verify mouse actions reject out-of-bounds coordinates and invalid buttons."""
    action = MouseAction("mouse.click")

    # Valid click
    res = action.run({"x": 500, "y": 300, "button": "left"})
    assert res["executed"] is True
    assert res["x"] == 500

    # Negative coordinates
    with pytest.raises(ValueError, match="display boundaries"):
        action.run({"x": -10, "y": 200})

    # Out of bounds coordinates (exceeding 8K)
    with pytest.raises(ValueError, match="display boundaries"):
        action.run({"x": 10000, "y": 200})

    # Invalid button
    with pytest.raises(ValueError, match="Invalid mouse button"):
        action.run({"x": 100, "y": 100, "button": "destroy"})


def test_sensitive_field_detection_and_refusal():
    """Verify SensitiveContextDetector detects credential contexts and KeyboardAction halts."""
    # 1. Direct detector checks
    assert SensitiveContextDetector.is_sensitive_context(ui_context="Password Input")[0] is True
    assert SensitiveContextDetector.is_sensitive_context(ui_context="Enter your OTP code")[0] is True
    assert (
        SensitiveContextDetector.is_sensitive_context(text_to_type="sk_live_1234567890abcdef123456")[0]
        is True
    )
    assert (
        SensitiveContextDetector.is_sensitive_context(ui_context="Search input", text_to_type="Hello Kairo")[
            0
        ]
        is False
    )

    # 2. Keyboard Action halts when typing into sensitive field
    kb_action = KeyboardAction("keyboard.type")
    with pytest.raises(PermissionError, match="Refusing to type into sensitive context"):
        kb_action.run({"text": "SuperSecret123!", "target_context": "User Password Field"})

    # 3. Non-sensitive typing succeeds
    res = kb_action.run({"text": "print('hello')", "target_context": "code editor"})
    assert res["executed"] is True
    assert res["characters_typed"] == len("print('hello')")
