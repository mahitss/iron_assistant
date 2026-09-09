"""Adaptive trace sampling with error and security event prioritization (Task 38)."""

import random
from app.observability.schemas import Trace, TraceStatus


class TraceSampler:
    """Evaluates whether a trace should be persisted or retained based on risk and outcome."""

    def __init__(self, default_sample_rate: float = 0.20) -> None:
        self.default_sample_rate = max(0.0, min(1.0, default_sample_rate))

    def should_sample(self, trace: Trace) -> bool:
        """Determines if a trace should be retained in durable storage.

        Rules:
        1. Always retain (100%) traces with errors, timeouts, or degraded status.
        2. Always retain (100%) traces involving security, policy denials, or financial operations.
        3. Probabilistically sample low-value successful traces.
        """
        # 1. Error / Failure prioritization
        if trace.status in (TraceStatus.ERROR, TraceStatus.TIMEOUT, TraceStatus.DEGRADED) or trace.error_count > 0:
            return True

        # 2. Critical operations (security, policy, recovery)
        metadata = trace.metadata or {}
        if metadata.get("is_critical") or metadata.get("is_security_event") or metadata.get("policy_denied"):
            return True

        # Check if any span had an error or security tag
        for span in trace.spans:
            if span.error_code is not None or span.attributes.get("security_event"):
                return True

        # 3. Probabilistic sampling for routine successes
        return random.random() < self.default_sample_rate
