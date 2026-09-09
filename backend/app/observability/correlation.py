"""Contextual correlation propagation across async coroutines, subagents, and workers (Task 38)."""

from contextvars import ContextVar
from typing import Any

from app.observability.schemas import CorrelationMetadata

_CURRENT_TRACE_ID: ContextVar[str | None] = ContextVar("current_trace_id", default=None)
_CURRENT_SPAN_ID: ContextVar[str | None] = ContextVar("current_span_id", default=None)
_CURRENT_TASK_ID: ContextVar[str | None] = ContextVar("current_task_id", default=None)
_CURRENT_STEP_ID: ContextVar[str | None] = ContextVar("current_step_id", default=None)
_CURRENT_USER_ID: ContextVar[str | None] = ContextVar("current_user_id", default=None)
_CURRENT_SESSION_ID: ContextVar[str | None] = ContextVar("current_session_id", default=None)
_CURRENT_PROJECT_ID: ContextVar[str | None] = ContextVar("current_project_id", default=None)
_CURRENT_CORRELATION_ID: ContextVar[str | None] = ContextVar("current_correlation_id", default=None)


def set_correlation_context(
    trace_id: str | None = None,
    span_id: str | None = None,
    task_id: str | None = None,
    step_id: str | None = None,
    user_id: str | None = None,
    session_id: str | None = None,
    project_id: str | None = None,
    correlation_id: str | None = None,
) -> None:
    """Updates active context variables for the current async task/thread."""
    if trace_id is not None:
        _CURRENT_TRACE_ID.set(trace_id)
    if span_id is not None:
        _CURRENT_SPAN_ID.set(span_id)
    if task_id is not None:
        _CURRENT_TASK_ID.set(task_id)
    if step_id is not None:
        _CURRENT_STEP_ID.set(step_id)
    if user_id is not None:
        _CURRENT_USER_ID.set(user_id)
    if session_id is not None:
        _CURRENT_SESSION_ID.set(session_id)
    if project_id is not None:
        _CURRENT_PROJECT_ID.set(project_id)
    if correlation_id is not None:
        _CURRENT_CORRELATION_ID.set(correlation_id)


def get_current_trace_id() -> str | None:
    return _CURRENT_TRACE_ID.get()


def get_current_span_id() -> str | None:
    return _CURRENT_SPAN_ID.get()


def get_current_task_id() -> str | None:
    return _CURRENT_TASK_ID.get()


def get_current_correlation() -> CorrelationMetadata:
    """Returns the aggregated current correlation metadata."""
    tid = _CURRENT_TRACE_ID.get() or "trc_untraced"
    cid = _CURRENT_CORRELATION_ID.get() or tid
    return CorrelationMetadata(
        trace_id=tid,
        correlation_id=cid,
        task_id=_CURRENT_TASK_ID.get(),
        step_id=_CURRENT_STEP_ID.get(),
        user_id=_CURRENT_USER_ID.get(),
        project_id=_CURRENT_PROJECT_ID.get(),
    )
