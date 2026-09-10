"""Safety boundaries, prompt injection defense, secret scrubbing, and execution firewall for Research Engine (Task 63)."""

from __future__ import annotations

import re
from typing import Any


class ResearchSafetyError(Exception):
    """Base exception for research engine safety violations."""


class ResearchExecutionBoundaryError(ResearchSafetyError):
    """Raised when research engine attempts direct tool side-effects or unauthorized execution."""


# Secret and credential regex scrubbers
_SECRET_PATTERNS = [
    (
        re.compile(
            r'(?i)(password|secret|api[_-]?key|token|auth[_-]?token|bearer|private[_-]?key)\s*[:=]\s*["\']?([a-zA-Z0-9_\-\.]{8,})["\']?'
        ),
        r"\1: [REDACTED_SECRET]",
    ),
    (re.compile(r"(?i)(bearer\s+)([a-zA-Z0-9_\-\.]{15,})"), r"\1[REDACTED_SECRET]"),
    (
        re.compile(r"(?i)-----BEGIN [A-Z ]+ PRIVATE KEY-----[\s\S]+?-----END [A-Z ]+ PRIVATE KEY-----"),
        r"[REDACTED_SECRET]",
    ),
    (re.compile(r"(?i)AKIA[0-9A-Z]{16}"), r"[REDACTED_SECRET]"),
    (re.compile(r"(?i)(?:ghp|gho)_[a-zA-Z0-9]{36}"), r"[REDACTED_SECRET]"),
]

# Prompt injection and malicious research directive indicators
_INJECTION_PATTERNS = [
    "delete all databases",
    "drop table",
    "rm -rf",
    "ignore previous instructions",
    "ignore your security rules",
    "bypass authorization",
    "grant root",
    "disable security",
    "override policy",
    "elevate privilege",
    "execute this command",
    "unrestricted production tool",
    "disable approval",
    "skip verification",
    "disable audit",
]


def scrub_research_secrets(text: str) -> str:
    """Scrub sensitive credentials, tokens, and private keys from research text."""
    if not text:
        return text
    scrubbed = text
    for pattern, replacement in _SECRET_PATTERNS:
        scrubbed = pattern.sub(replacement, scrubbed)
    return scrubbed


def sanitize_research_directive(directive: str, raise_on_violation: bool = False) -> str:
    """Detect and neutralize prompt injection attempts in research queries, documents, and external text.

    Invariant 49 & 51: RESEARCH CONTENT != SYSTEM INSTRUCTION. External text remains passive data.
    """
    if not directive:
        return directive
    cleaned = directive
    for indicator in _INJECTION_PATTERNS:
        pattern = re.compile(re.escape(indicator), re.IGNORECASE)
        if pattern.search(cleaned):
            if raise_on_violation:
                raise ResearchSafetyError(
                    f"Malicious directive or prompt injection detected in research content: '{indicator}'"
                )
            cleaned = pattern.sub("[NEUTRALIZED_DIRECTIVE]", cleaned)
    # Also neutralize system instruction directives
    cleaned = re.sub(r"(?i)\bsystem\s+instruction\s*:\s*", "[NEUTRALIZED_DIRECTIVE]: ", cleaned)
    return scrub_research_secrets(cleaned.strip())


_ALLOWED_READ_ONLY_ACTIONS = {
    "web_search",
    "read_document",
    "query_knowledge_graph",
    "fetch_source",
    "retrieve",
    "extract_claims",
    "extract_evidence",
    "synthesize",
    "get_timeline",
    "audit_trail",
}


def block_direct_research_action(action_name: str, context: dict[str, Any] | None = None) -> None:
    """Invariant enforcement: Research engine discovers and synthesizes, but NEVER directly executes tools.

    All execution must flow through:
    Research -> Plan -> Policy -> Authorization -> Approval -> ToolExecutor -> Verification.
    """
    if action_name in _ALLOWED_READ_ONLY_ACTIONS or action_name.startswith(
        ("read_", "query_", "search_", "fetch_")
    ):
        return
    raise ResearchExecutionBoundaryError(
        f"Execution Boundary Violation: Research engine cannot directly execute action '{action_name}'. "
        "Execution must be routed through Policy, Authorization, Approval, and ToolExecutor."
    )
