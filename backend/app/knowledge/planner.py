"""Retrieval planner that determines intent, optimal sources, and query strategy."""

import logging
import re
from app.knowledge.schemas import (
    RAGQuery,
    RAGSourceType,
    RetrievalIntent,
    RetrievalPlan,
    TrustTier,
)

logger = logging.getLogger("kairo.knowledge.planner")


class RetrievalPlanner:
    """Classifies user intent and formulates optimized multi-source retrieval plans."""

    def plan(self, query: RAGQuery) -> RetrievalPlan:
        """Analyze query parameters, text, and context to generate a targeted RetrievalPlan."""
        raw_text = query.text.lower()

        # 1. Intent Classification
        intent = self._classify_intent(raw_text)

        # 2. Source Selection
        if query.sources:
            # Explicit user override
            sources = query.sources
        else:
            sources = self._select_sources_for_intent(intent, raw_text)

        # 3. Weights calculation
        use_bm25 = True
        use_vector = True
        use_code_intel = intent in {RetrievalIntent.CODE_SEARCH, RetrievalIntent.DEBUGGING}

        if intent == RetrievalIntent.CODE_SEARCH:
            bm25_w = 0.5
            vector_w = 0.3
            code_w = 0.2
        elif intent == RetrievalIntent.FACTUAL:
            bm25_w = 0.4
            vector_w = 0.6
            code_w = 0.0
        elif intent == RetrievalIntent.TEMPORAL:
            bm25_w = 0.3
            vector_w = 0.7
            code_w = 0.0
        else:
            bm25_w = 0.35
            vector_w = 0.65
            code_w = 0.0

        # Sub-queries generation (decomposed search queries)
        sub_queries = self._generate_sub_queries(query.text, intent)

        # Freshness / Trust requirements
        min_trust = TrustTier.WEB_SCRAPED if RAGSourceType.WEB_SEARCH in sources else TrustTier.USER_UPLOAD

        return RetrievalPlan(
            original_query=query.text,
            intent=intent,
            selected_sources=sources,
            sub_queries=sub_queries,
            use_bm25=use_bm25,
            use_vector=use_vector,
            use_code_intel=use_code_intel,
            bm25_weight=bm25_w,
            vector_weight=vector_w,
            code_symbol_weight=code_w,
            min_trust_tier=min_trust,
            target_limit=query.limit,
            target_token_budget=query.token_budget,
        )

    def _classify_intent(self, text: str) -> RetrievalIntent:
        # Code search indicators
        if any(w in text for w in [
            "function", "class", "method", "def ", "import ", "syntax", "endpoint",
            "symbol", "call stack", "where is", "implementation of", ".py", ".ts", ".js",
        ]):
            return RetrievalIntent.CODE_SEARCH

        # Debugging indicators
        if any(w in text for w in ["traceback", "exception", "error", "failed", "bug", "crash", "stack trace"]):
            return RetrievalIntent.DEBUGGING

        # Temporal indicators
        if any(w in text for w in ["yesterday", "last week", "meeting", "transcript", "recording", "what happened at", "timeline"]):
            return RetrievalIntent.TEMPORAL

        # Summary indicators
        if any(w in text for w in ["summarize", "overview", "tl;dr", "brief", "summary of", "digest"]):
            return RetrievalIntent.SUMMARY

        # Factual indicators
        if any(w in text for w in ["what is", "how many", "who is", "when did", "which version", "config value"]):
            return RetrievalIntent.FACTUAL

        # Default to conceptual
        return RetrievalIntent.CONCEPTUAL

    def _select_sources_for_intent(self, intent: RetrievalIntent, text: str) -> list[RAGSourceType]:
        if intent == RetrievalIntent.CODE_SEARCH:
            return [RAGSourceType.CODE, RAGSourceType.GITHUB_REPO, RAGSourceType.DOCUMENT]

        if intent == RetrievalIntent.DEBUGGING:
            return [RAGSourceType.CODE, RAGSourceType.EVENT_BUS, RAGSourceType.DOCUMENT, RAGSourceType.WORLD_MODEL]

        if intent == RetrievalIntent.TEMPORAL:
            return [RAGSourceType.AUDIO_TRANSCRIPT, RAGSourceType.MEMORY, RAGSourceType.EVENT_BUS]

        if "latest" in text or "news" in text or "web" in text:
            return [RAGSourceType.WEB_SEARCH, RAGSourceType.DOCUMENT]

        # Broad conceptual/factual default
        return [RAGSourceType.DOCUMENT, RAGSourceType.MARKDOWN, RAGSourceType.PDF, RAGSourceType.MEMORY]

    def _generate_sub_queries(self, query: str, intent: RetrievalIntent) -> list[str]:
        sub: list[str] = [query]
        # Clean query for BM25 (strip punctuation)
        clean = re.sub(r"[^\w\s]", " ", query).strip()
        if clean and clean != query:
            sub.append(clean)

        # Extract symbol or identifier if present (e.g. CamelCase or snake_case word)
        identifiers = re.findall(r"\b[a-zA-Z_][a-zA-Z0-9_]{3,}\b", query)
        for ident in identifiers:
            if "_" in ident or any(c.isupper() for c in ident[1:]):
                sub.append(ident)

        return list(dict.fromkeys(sub))[:4]
