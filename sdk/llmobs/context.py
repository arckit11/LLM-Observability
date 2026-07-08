"""Trace context management for the LLM observability SDK.

Provides lightweight context propagation so that multiple observed calls
within the same logical operation share a single ``trace_id``.

Usage::

    from llmobs.context import trace

    with trace(name="my-pipeline", session_id="user-123"):
        # All @observe calls inside this block share the same trace_id
        result = my_llm_call(...)
"""

from __future__ import annotations

import uuid
from contextvars import ContextVar, Token
from typing import Optional


# ---------------------------------------------------------------------------
# Context variables
# ---------------------------------------------------------------------------

_current_trace_id: ContextVar[Optional[str]] = ContextVar(
    "llmobs_trace_id", default=None
)
_current_session_id: ContextVar[Optional[str]] = ContextVar(
    "llmobs_session_id", default=None
)


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def new_span_id() -> str:
    """Generate a short, unique span identifier (first 8 hex chars of a UUID4)."""
    return uuid.uuid4().hex[:8]


def get_current_trace_id() -> str:
    """Return the current trace ID, creating one if none is set.

    If called outside a :class:`trace` context manager the function will
    auto-generate a new trace ID so that standalone ``@observe`` calls still
    produce valid events.
    """
    tid = _current_trace_id.get()
    if tid is None:
        tid = uuid.uuid4().hex
        _current_trace_id.set(tid)
    return tid


def get_current_session_id() -> Optional[str]:
    """Return the current session ID, or ``None`` if unset."""
    return _current_session_id.get()


# ---------------------------------------------------------------------------
# Context manager
# ---------------------------------------------------------------------------


class trace:
    """Context manager that establishes a shared trace scope.

    All ``@observe``-decorated calls executed inside a ``trace`` block will
    inherit the same ``trace_id``, making it easy to correlate related spans.

    Args:
        name: A human-readable label for the trace (informational only).
        session_id: Optional session identifier propagated to child spans.
        trace_id: Explicit trace ID.  If ``None`` a new UUID is generated.

    Example::

        with trace(name="rag-pipeline", session_id="sess_abc"):
            embedding = embed(query)
            answer    = generate(embedding)
    """

    def __init__(
        self,
        *,
        name: str = "trace",
        session_id: Optional[str] = None,
        trace_id: Optional[str] = None,
    ) -> None:
        self.name = name
        self.trace_id = trace_id or uuid.uuid4().hex
        self.session_id = session_id
        self._trace_token: Optional[Token[Optional[str]]] = None
        self._session_token: Optional[Token[Optional[str]]] = None

    # Sync context manager ------------------------------------------------

    def __enter__(self) -> "trace":
        self._trace_token = _current_trace_id.set(self.trace_id)
        if self.session_id is not None:
            self._session_token = _current_session_id.set(self.session_id)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:  # noqa: ANN001
        if self._trace_token is not None:
            _current_trace_id.reset(self._trace_token)
        if self._session_token is not None:
            _current_session_id.reset(self._session_token)

    # Async context manager ------------------------------------------------

    async def __aenter__(self) -> "trace":
        return self.__enter__()

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:  # noqa: ANN001
        self.__exit__(exc_type, exc_val, exc_tb)
