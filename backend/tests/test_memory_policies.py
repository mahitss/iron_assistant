"""Unit tests for MemoryPolicy deterministic validation, secret prevention, and quality filters."""

from app.memory.policies import MemoryPolicy
from app.memory.schemas import MemoryCandidate, MemoryType


def test_policy_accepts_valid_preference():
    """Verify clean user preference is accepted with importance adjustment."""
    cand = MemoryCandidate(
        content="The user prefers dark mode interfaces.",
        memory_type=MemoryType.PREFERENCE,
        importance=0.4,
    )
    decision = MemoryPolicy.evaluate(cand)
    assert decision.accepted is True
    assert decision.sanitized_content == "The user prefers dark mode interfaces."
    assert decision.rejection_reason is None
    # Preferences have a minimum baseline of 0.6
    assert decision.importance >= 0.6


def test_policy_accepts_project_fact():
    """Verify project fact candidate is accepted."""
    cand = MemoryCandidate(
        content="The user is building Kairo with PostgreSQL and pgvector.",
        memory_type=MemoryType.PROJECT,
        importance=0.75,
    )
    decision = MemoryPolicy.evaluate(cand)
    assert decision.accepted is True
    assert decision.importance == 0.75
    assert decision.rejection_reason is None


def test_policy_rejects_one_off_arithmetic():
    """Verify pure math expressions and one-off calculations are rejected."""
    math_examples = [
        "25 * 4 = 100",
        "calculate 10 + 20",
        "100 / 2",
        "what is 50 + 50?",
    ]
    for expr in math_examples:
        cand = MemoryCandidate(content=expr, memory_type=MemoryType.FACT)
        decision = MemoryPolicy.evaluate(cand)
        assert decision.accepted is False
        assert any(term in decision.rejection_reason.lower() for term in ["arithmetic", "calculation", "question"])


def test_policy_rejects_casual_filler():
    """Verify casual conversational filler is rejected."""
    casual_examples = [
        "hello!",
        "Good morning",
        "Thank you",
        "goodbye",
    ]
    for text in casual_examples:
        cand = MemoryCandidate(content=text, memory_type=MemoryType.CONTEXT)
        decision = MemoryPolicy.evaluate(cand)
        assert decision.accepted is False
        assert "conversational filler" in decision.rejection_reason.lower()


def test_policy_rejects_debugging_stack_trace():
    """Verify transient error stack traces are rejected."""
    stack_trace = 'Traceback (most recent call last):\n  File "main.py", line 12, in <module>'
    cand = MemoryCandidate(content=stack_trace, memory_type=MemoryType.FACT)
    decision = MemoryPolicy.evaluate(cand)
    assert decision.accepted is False
    assert "debug" in decision.rejection_reason.lower() or "stack trace" in decision.rejection_reason.lower()


def test_policy_rejects_secrets_and_credentials():
    """Verify sensitive tokens and passwords trigger policy rejection."""
    secret_cand = MemoryCandidate(
        content="The secret key is pk_test_sample_token_secret_1234567890abcdef",
        memory_type=MemoryType.FACT,
    )
    decision = MemoryPolicy.evaluate(secret_cand)
    assert decision.accepted is False
    assert "credentials" in decision.rejection_reason.lower() or "keys" in decision.rejection_reason.lower()


def test_policy_rejects_oversized_content():
    """Verify candidates exceeding 500 characters are rejected."""
    long_text = "Durable memory info. " * 30  # > 600 characters
    cand = MemoryCandidate.model_construct(content=long_text, memory_type=MemoryType.FACT, importance=0.5)
    decision = MemoryPolicy.evaluate(cand)
    assert decision.accepted is False
    assert "maximum length" in decision.rejection_reason.lower()


def test_policy_rejects_undersized_content():
    """Verify candidates shorter than 5 characters are rejected."""
    cand = MemoryCandidate(content="Abc", memory_type=MemoryType.FACT)
    decision = MemoryPolicy.evaluate(cand)
    assert decision.accepted is False
    assert "too short" in decision.rejection_reason.lower()
