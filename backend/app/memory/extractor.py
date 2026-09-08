"""Intelligent memory extraction using configured model capabilities and structured output."""

import json
import logging
import re
from typing import Any, Dict, List, Optional

from app.memory.schemas import MemoryCandidate, MemoryType
from app.models.provider import ChatMessage, MessageRole, ModelProvider
from app.models.registry import ModelCapability
from app.models.router import ModelRouter

logger = logging.getLogger("kairo.memory.extractor")

EXTRACTION_SYSTEM_PROMPT = (
    "You are Kairo's Memory Extractor. "
    "Analyze the conversation turn and identify only durable, persistent user information "
    "likely to be valuable across future sessions (such as user preferences, technical stacks, "
    "project facts, or standing instructions).\n"
    "CRITICAL RULES:\n"
    "- Do NOT extract temporary questions, casual conversation, greetings, or one-off arithmetic.\n"
    "- NEVER extract passwords, API keys, credentials, or private tokens.\n"
    "- Express memories in declarative statements (e.g., 'The user prefers dark mode.').\n"
    '- If nothing durable is present, return an empty list: {"candidates": []}.\n\n'
    "Allowed memory_type values: preference, fact, project, instruction, context.\n\n"
    "Respond ONLY with valid JSON in this exact format:\n"
    "{\n"
    '  "candidates": [\n'
    "    {\n"
    '      "content": "The user prefers Python for data analysis.",\n'
    '      "memory_type": "preference",\n'
    '      "importance": 0.8,\n'
    '      "reason": "Explicit language preference stated by user"\n'
    "    }\n"
    "  ]\n"
    "}"
)


class MemoryExtractor:
    """Extracts structured candidate memories from dialogue turns using model routing."""

    def __init__(
        self,
        provider: ModelProvider,
        router: Optional[ModelRouter] = None,
        capability: str = "fast",
        default_model: str = "openrouter/free",
    ):
        self.provider = provider
        self.router = router
        self.capability = capability
        self.default_model = default_model

    def resolve_model(self) -> str:
        """Resolve model ID using configured capability or fallback."""
        if self.router is not None:
            try:
                cap = ModelCapability.from_str(self.capability)
                model_def = self.router.select_model(cap)
                return model_def.id
            except Exception as exc:
                logger.debug(
                    "Failed to route extraction capability '%s': %s. Using default.", self.capability, exc
                )
        return self.default_model

    @staticmethod
    def _clean_json_text(text: str) -> str:
        """Strip markdown json code blocks or prefix/suffix chatter."""
        cleaned = text.strip()
        code_block = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, re.DOTALL)
        if code_block:
            return code_block.group(1).strip()
        # Find outermost brackets
        brace_start = cleaned.find("{")
        brace_end = cleaned.rfind("}")
        if brace_start != -1 and brace_end != -1 and brace_end > brace_start:
            return cleaned[brace_start : brace_end + 1]
        return cleaned

    def parse_candidates(self, raw_response: str) -> List[MemoryCandidate]:
        """Parse and validate JSON candidate list from model text."""
        if not raw_response or not raw_response.strip():
            return []

        json_text = self._clean_json_text(raw_response)
        try:
            data: Dict[str, Any] = json.loads(json_text)
        except json.JSONDecodeError as exc:
            logger.debug("MemoryExtractor: Failed to decode JSON from model: %s", exc)
            return []

        raw_candidates = data.get("candidates", [])
        if not isinstance(raw_candidates, list):
            return []

        parsed: List[MemoryCandidate] = []
        for item in raw_candidates:
            if not isinstance(item, dict):
                continue
            content = item.get("content")
            if not content or not isinstance(content, str):
                continue

            raw_type = item.get("memory_type", "fact")
            try:
                m_type = MemoryType(str(raw_type).lower())
            except ValueError:
                # Reject invalid memory types
                continue

            try:
                imp = float(item.get("importance", 0.5))
                imp = max(0.0, min(1.0, imp))
            except (ValueError, TypeError):
                imp = 0.5

            reason = str(item.get("reason", ""))[:200] if item.get("reason") else None

            try:
                candidate = MemoryCandidate(
                    content=content.strip(),
                    memory_type=m_type,
                    importance=imp,
                    reason=reason,
                )
                parsed.append(candidate)
            except Exception as exc:
                logger.debug("Discarding invalid candidate: %s", exc)

        return parsed

    async def extract_candidates(
        self,
        user_message: str,
        assistant_response: str,
    ) -> List[MemoryCandidate]:
        """Extract durable candidate memories from a single conversation turn."""
        turn_text = f"User: {user_message}\nAssistant: {assistant_response}"

        messages = [
            ChatMessage(role=MessageRole.SYSTEM, content=EXTRACTION_SYSTEM_PROMPT),
            ChatMessage(role=MessageRole.USER, content=f"Conversation turn:\n{turn_text}"),
        ]

        model = self.resolve_model()

        try:
            resp = await self.provider.generate_response(messages, model=model)
            raw_text = getattr(resp, "content", None) or str(resp)
            candidates = self.parse_candidates(raw_text)
            logger.debug("MemoryExtractor extracted %d candidates using model %s", len(candidates), model)
            return candidates
        except Exception as exc:
            logger.warning("Memory extraction failed safely (%s). Continuing without new memories.", exc)
            return []
