"""Unit tests for capability modeling, tool health tracking, and anti-hallucination controls."""

import pytest

from app.metacognition.capabilities import (
    CapabilityHallucinationError,
    CapabilityManager,
)
from app.metacognition.schemas import CapabilityState


def test_capability_discovery_and_anti_hallucination():
    cm = CapabilityManager()

    # Valid capability lookup
    cap = cm.check_capability("web_research")
    assert cap.name == "web_research"
    assert "web_search" in cap.tools

    # Invariant 6: Cannot hallucinate non-existent capabilities
    with pytest.raises(CapabilityHallucinationError, match="does not exist in registered system"):
        cm.check_capability("teleportation_engine")


def test_degraded_capability_from_tool_failure():
    cm = CapabilityManager()

    # Initial state is AVAILABLE
    web_cap = cm.get_capability("web_research")
    assert web_cap.state == CapabilityState.AVAILABLE.value

    # Invariants 8 & 9: Mark tool failing -> parent capability becomes DEGRADED
    cm.update_tool_health("web_search", is_healthy=False, error_msg="DNS timeout / rate limit")

    web_cap_updated = cm.get_capability("web_research")
    assert web_cap_updated.state == CapabilityState.DEGRADED.value
    assert "DNS timeout" in web_cap_updated.degradation_reason
    assert web_cap_updated.confidence < 1.0

    # Invariant 13: Alternatives suggested
    assert len(web_cap_updated.alternatives) > 0

    # Tool recovers
    cm.update_tool_health("web_search", is_healthy=True)
    web_cap_recovered = cm.get_capability("web_research")
    assert web_cap_recovered.state == CapabilityState.AVAILABLE.value
    assert web_cap_recovered.confidence == 1.0
