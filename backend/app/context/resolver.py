"""Context resolver using deterministic signals first, followed by hybrid memory, workflow, and proactive context."""

import logging
import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.automation.models import WorkflowRun
from app.context.project import ProjectService
from app.context.ranking import ContextRanker
from app.context.safety import ContextSafetyGuard
from app.context.schemas import (
    ContextItem,
    ContextPacket,
    ContextType,
    ProjectResponse,
)
from app.context.session import SessionContextManager
from app.memory.service import MemoryService
from app.proactive.models import ProactiveInsight

logger = logging.getLogger("kairo.context.resolver")


class ContextResolver:
    """Resolves relevant context by prioritizing deterministic signals before hybrid search."""

    def __init__(
        self,
        session_manager: SessionContextManager | None = None,
        max_context_items: int = 30,
        max_memory_items: int = 10,
        max_project_items: int = 10,
    ) -> None:
        self.session_manager = session_manager or SessionContextManager()
        self.max_context_items = max_context_items
        self.max_memory_items = max_memory_items
        self.max_project_items = max_project_items

    async def resolve(
        self,
        user_id: str,
        message: str,
        session_id: str | None = None,
        db_session: AsyncSession | None = None,
        memory_service: MemoryService | None = None,
        user_timezone: str = "UTC",
    ) -> ContextPacket:
        """Deterministically resolve, score, sanitize, and bound context for a user turn."""
        q_clean = (message or "").strip()
        query_words = set(re.findall(r"\b[a-zA-Z0-9_\-]{3,}\b", q_clean.lower()))

        candidate_items: list[ContextItem] = []
        ambiguous_projects: list[str] = []
        active_project: ProjectResponse | None = None

        # 1. Ephemeral Session Context
        session_ctx = {}
        if session_id:
            session_ctx = await self.session_manager.get_session_context(session_id)
            for outcome in session_ctx.get("recent_tool_outcomes", []):
                candidate_items.append(
                    ContextItem(
                        source_type=ContextType.SESSION_CONTEXT,
                        source_id=f"tool_outcome_{outcome.get('tool')}",
                        title=f"Recent Tool: {outcome.get('tool')}",
                        content=f"Executed with status '{outcome.get('status')}'. {outcome.get('summary', '')}".strip(),
                        relevance_score=0.60,
                        confidence=1.0,
                        reason="Executed earlier in current conversation session.",
                    )
                )

        # 2. Deterministic Project Resolution
        if db_session is not None:
            try:
                proj_service = ProjectService(db_session)
                user_projects = await proj_service.list_projects(user_id=user_id, limit=50)

                # Check explicit mentions in user query
                matched_projects: list[ProjectResponse] = []
                for p in user_projects:
                    p_name_lower = p.name.lower()
                    if p_name_lower in q_clean.lower() or any(
                        repo.lower() in q_clean.lower() for repo in p.repositories
                    ):
                        matched_projects.append(p)

                if len(matched_projects) == 1:
                    active_project = matched_projects[0]
                elif len(matched_projects) > 1:
                    ambiguous_projects = [p.name for p in matched_projects]
                    # Default to the one with highest recency if not risky
                    active_project = matched_projects[0]
                elif session_ctx.get("active_project_id"):
                    # Use project pinned to session
                    active_project = await proj_service.get_project(
                        user_id=user_id, project_id=session_ctx["active_project_id"]
                    )
                elif user_projects:
                    # Fallback to most recently active project if only one exists or query is general
                    active_project = user_projects[0]

                if active_project:
                    # Add project context items
                    desc = f": {active_project.description}" if active_project.description else ""
                    candidate_items.append(
                        ContextItem(
                            source_type=ContextType.PROJECT_CONTEXT,
                            source_id=active_project.id,
                            title=f"Project {active_project.name}",
                            content=f"Status is {active_project.status.value}{desc}",
                            relevance_score=0.85,
                            confidence=1.0,
                            reason="Active project context.",
                        )
                    )
                    for repo in active_project.repositories:
                        candidate_items.append(
                            ContextItem(
                                source_type=ContextType.DEVELOPER_CONTEXT,
                                source_id=f"repo_{repo}",
                                title="Linked Repository",
                                content=repo,
                                relevance_score=0.75,
                                confidence=1.0,
                                reason=f"Repository linked to project '{active_project.name}'.",
                            )
                        )
            except Exception as exc:
                logger.debug("Project resolution error in context resolver: %s", exc)

        # 3. Ambiguity & Risky Intent Check
        requires_disambiguation = False
        clarification_prompt = None
        if len(ambiguous_projects) > 1:
            requires_disambiguation, clarification_prompt = ContextSafetyGuard.check_project_ambiguity(
                user_message=q_clean,
                matching_projects=ambiguous_projects,
            )

        # 4. Relevant Workflow Runs
        if db_session is not None:
            try:
                wf_stmt = (
                    select(WorkflowRun)
                    .where(WorkflowRun.user_id == user_id)
                    .order_by(WorkflowRun.created_at.desc())
                    .limit(5)
                )
                wf_res = await db_session.execute(wf_stmt)
                recent_runs = wf_res.scalars().all()
                for run in recent_runs:
                    status_upper = run.status.upper()
                    # High relevance if failed or pending, or if user explicitly mentioned workflow/run
                    rel = 0.80 if status_upper in ("FAILED", "PENDING") else 0.40
                    candidate_items.append(
                        ContextItem(
                            source_type=ContextType.WORKFLOW_CONTEXT,
                            source_id=run.id,
                            title=f"Workflow Run #{run.id[:8]}",
                            content=f"Status: {status_upper}. Error: {run.error or 'None'}",
                            relevance_score=rel,
                            confidence=1.0,
                            timestamp=run.created_at,
                            reason=f"Recent workflow execution with status {status_upper}.",
                        )
                    )
            except Exception as exc:
                logger.debug("Failed querying workflow context: %s", exc)

        # 5. Relevant Proactive Insights
        if db_session is not None:
            try:
                ins_stmt = (
                    select(ProactiveInsight)
                    .where(
                        ProactiveInsight.user_id == user_id,
                        ProactiveInsight.status.in_(["new", "delivered"]),
                    )
                    .order_by(ProactiveInsight.created_at.desc())
                    .limit(5)
                )
                ins_res = await db_session.execute(ins_stmt)
                insights = ins_res.scalars().all()
                for ins in insights:
                    rel = 0.85 if ins.priority == "HIGH" else 0.50
                    candidate_items.append(
                        ContextItem(
                            source_type=ContextType.PROACTIVE_CONTEXT,
                            source_id=ins.id,
                            title=f"Alert: {ins.title}",
                            content=ins.summary,
                            relevance_score=rel,
                            confidence=0.9,
                            timestamp=ins.created_at,
                            reason=f"Proactive notification with priority {ins.priority}.",
                        )
                    )
            except Exception as exc:
                logger.debug("Failed querying proactive context: %s", exc)

        # 6. Hybrid Memory Retrieval (Semantic + Keyword + Scoped)
        if memory_service is not None and q_clean:
            try:
                mem_results = await memory_service.search_memories(
                    query=q_clean,
                    top_k=self.max_memory_items,
                )
                for res in mem_results:
                    # Score memory higher if related to active project
                    mem_score = res.score
                    mem_type = getattr(res.memory.memory_type, "value", str(res.memory.memory_type))
                    candidate_items.append(
                        ContextItem(
                            source_type=ContextType.MEMORY_CONTEXT,
                            source_id=res.memory.id,
                            title=f"Memory ({mem_type})",
                            content=res.memory.content,
                            relevance_score=mem_score,
                            confidence=0.95,
                            timestamp=res.memory.updated_at,
                            reason=f"Hybrid memory search match (similarity: {res.similarity:.2f}).",
                        )
                    )
            except Exception as exc:
                logger.debug("Memory search error in context resolver: %s", exc)

        # 6.5. Relevant Knowledge Fabric Retrieval
        if db_session is not None and q_clean:
            try:
                from app.knowledge.schemas import KnowledgeSearchRequest
                from app.knowledge.service import KnowledgeFabricService

                knowledge_svc = KnowledgeFabricService()
                k_req = KnowledgeSearchRequest(
                    query=q_clean,
                    project_id=active_project.id if active_project else None,
                    limit=min(8, self.max_context_items // 3),
                )
                k_results = await knowledge_svc.search(db_session, user_id=user_id, request=k_req)
                for k_item in k_results:
                    candidate_items.append(
                        ContextItem(
                            source_type=ContextType.KNOWLEDGE_CONTEXT,
                            source_id=k_item.id,
                            title=f"Knowledge ({k_item.type.value if hasattr(k_item.type, 'value') else k_item.type}): {k_item.title}",
                            content=k_item.summary,
                            relevance_score=k_item.relevance,
                            confidence=k_item.confidence,
                            timestamp=k_item.timestamp,
                            provenance=k_item.source_type,
                            reason=k_item.explanation or "Knowledge Fabric hybrid retrieval match.",
                        )
                    )
            except Exception as exc:
                logger.debug("Knowledge Fabric retrieval error in context resolver: %s", exc)

        # 6.6. Relevant Long-Term Experience and Preference Retrieval (Task 29)
        if q_clean:
            try:
                from app.experience.retrieval import ExperienceRetriever

                exp_retriever = ExperienceRetriever()
                experiences, preferences = await exp_retriever.retrieve_relevant_experiences(
                    user_id=user_id,
                    query=q_clean,
                    project_id=active_project.id if active_project else None,
                    db_session=db_session,
                )

                for pref in preferences:
                    scope_str = pref.scope.value if hasattr(pref.scope, "value") else str(pref.scope)
                    candidate_items.append(
                        ContextItem(
                            source_type=ContextType.EXPERIENCE_CONTEXT,
                            source_id=f"pref_{pref.id}",
                            title=f"User Preference ({scope_str}): {pref.key}",
                            content=f"USER PREFERENCE [{scope_str}]: {pref.key} = {pref.value}",
                            relevance_score=0.90,
                            confidence=1.0 if getattr(pref.confidence, "value", str(pref.confidence)) == "HIGH" else 0.8,
                            timestamp=pref.updated_at,
                            provenance="user_preference",
                            reason="Active user preference.",
                        )
                    )

                for exp in experiences:
                    exp_type_str = exp.type.value if hasattr(exp.type, "value") else str(exp.type)
                    candidate_items.append(
                        ContextItem(
                            source_type=ContextType.EXPERIENCE_CONTEXT,
                            source_id=f"exp_{exp.id}",
                            title=f"Experience ({exp_type_str}): {exp.summary[:50]}",
                            content=f"EXPERIENCE [{exp_type_str}]: {exp.summary}",
                            relevance_score=0.85,
                            confidence=0.9 if getattr(exp.confidence, "value", str(exp.confidence)) == "HIGH" else 0.7,
                            timestamp=exp.updated_at,
                            provenance=exp.source.value if hasattr(exp.source, "value") else str(exp.source),
                            reason="Relevant past experience.",
                        )
                    )
            except Exception as exc:
                logger.debug("Experience retrieval error in context resolver: %s", exc)

        # 7. Rescore candidates with multi-factor ranker
        active_pid = active_project.id if active_project else None
        for idx, it in enumerate(candidate_items):
            rescored = ContextRanker.score_item(
                item=it,
                user_query=q_clean,
                active_project_id=active_pid,
                query_terms=query_words,
            )
            candidate_items[idx] = it.model_copy(update={"relevance_score": rescored})

        # 8. Sanitize & Filter Sensitive Data
        sanitized_items: list[ContextItem] = []
        for it in candidate_items:
            clean_item = ContextSafetyGuard.sanitize_item(it)
            if clean_item:
                sanitized_items.append(clean_item)

        # 9. Rank & Bound against Context Budgets
        bounded_items = ContextRanker.rank_and_bound(
            items=sanitized_items,
            max_total=self.max_context_items,
            max_memories=self.max_memory_items,
            max_project_items=self.max_project_items,
        )

        # 10. Assemble Context Packet
        packet = ContextPacket(
            session_id=session_id,
            user_id=user_id,
            active_project=active_project,
            items=bounded_items,
            session_context=[i for i in bounded_items if i.source_type == ContextType.SESSION_CONTEXT],
            project_context=[i for i in bounded_items if i.source_type == ContextType.PROJECT_CONTEXT],
            conversation_context=[
                i for i in bounded_items if i.source_type == ContextType.CONVERSATION_CONTEXT
            ],
            memory_context=[i for i in bounded_items if i.source_type == ContextType.MEMORY_CONTEXT],
            workflow_context=[i for i in bounded_items if i.source_type == ContextType.WORKFLOW_CONTEXT],
            developer_context=[i for i in bounded_items if i.source_type == ContextType.DEVELOPER_CONTEXT],
            proactive_context=[i for i in bounded_items if i.source_type == ContextType.PROACTIVE_CONTEXT],
            ambiguous_projects=ambiguous_projects,
            requires_disambiguation=requires_disambiguation,
            clarification_prompt=clarification_prompt,
            total_items=len(bounded_items),
        )

        return packet
