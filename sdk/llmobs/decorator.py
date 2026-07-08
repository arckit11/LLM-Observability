"""The ``@observe`` decorator for automatic LLM call instrumentation.

Wrap any function that calls an LLM API to automatically capture:
  * Latency (via ``time.perf_counter``)
  * Token usage & estimated cost
  * Model name, prompt, and response text
  * Errors (recorded and then re-raised)

The decorator transparently handles both **sync** and **async** functions.

Usage::

    from llmobs import observe

    @observe(name="chat", tags={"team": "search"})
    def ask(question: str):
        return openai.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": question}],
        )
"""

from __future__ import annotations

import asyncio
import functools
import json
import logging
import time
from typing import Any, Callable, Dict, Optional

from llmobs.context import (
    get_current_session_id,
    get_current_trace_id,
    new_span_id,
)
from llmobs.cost import calculate_cost
from llmobs.queue import enqueue_trace
from llmobs.schema import TraceEvent

logger = logging.getLogger("llmobs.decorator")


# ---------------------------------------------------------------------------
# Response extraction helpers
# ---------------------------------------------------------------------------


def _extract_openai(result: Any) -> Dict[str, Any]:
    """Extract fields from an OpenAI-style response object.

    Expected structure::

        result.model           -> str
        result.usage.prompt_tokens       -> int
        result.usage.completion_tokens   -> int
        result.choices[0].message.content -> str
    """
    info: Dict[str, Any] = {}
    try:
        info["model"] = getattr(result, "model", "")
    except Exception:  # noqa: BLE001
        pass
    try:
        usage = result.usage
        info["tokens_in"] = getattr(usage, "prompt_tokens", 0) or 0
        info["tokens_out"] = getattr(usage, "completion_tokens", 0) or 0
    except Exception:  # noqa: BLE001
        pass
    try:
        info["response"] = result.choices[0].message.content or ""
    except Exception:  # noqa: BLE001
        pass
    return info


def _extract_anthropic(result: Any) -> Dict[str, Any]:
    """Extract fields from an Anthropic-style response object.

    Expected structure::

        result.model                  -> str
        result.usage.input_tokens     -> int
        result.usage.output_tokens    -> int
        result.content[0].text        -> str
    """
    info: Dict[str, Any] = {}
    try:
        info["model"] = getattr(result, "model", "")
    except Exception:  # noqa: BLE001
        pass
    try:
        usage = result.usage
        info["tokens_in"] = getattr(usage, "input_tokens", 0) or 0
        info["tokens_out"] = getattr(usage, "output_tokens", 0) or 0
    except Exception:  # noqa: BLE001
        pass
    try:
        info["response"] = result.content[0].text or ""
    except Exception:  # noqa: BLE001
        pass
    return info


def _extract_response_info(result: Any) -> Dict[str, Any]:
    """Auto-detect the provider format and extract response metadata."""
    # Try OpenAI first (has .choices)
    if hasattr(result, "choices"):
        return _extract_openai(result)
    # Try Anthropic (has .content as a list with .text)
    if hasattr(result, "content") and isinstance(getattr(result, "content", None), list):
        return _extract_anthropic(result)
    # Fallback — return whatever string representation we can get
    return {"response": str(result) if result is not None else ""}


def _extract_prompt(kwargs: Dict[str, Any]) -> str:
    """Serialise the ``messages`` kwarg (if present) into a string."""
    messages = kwargs.get("messages")
    if messages is None:
        return ""
    if isinstance(messages, str):
        return messages
    try:
        return json.dumps(messages, default=str)
    except Exception:  # noqa: BLE001
        return str(messages)


# ---------------------------------------------------------------------------
# Core emit helper
# ---------------------------------------------------------------------------


def _emit(
    *,
    func_name: str,
    session_id: Optional[str],
    tags: Dict[str, Any],
    kwargs: Dict[str, Any],
    result: Any,
    latency_ms: int,
    error: Optional[str],
) -> None:
    """Build a :class:`TraceEvent` and enqueue it for delivery."""
    try:
        info = _extract_response_info(result) if result is not None else {}

        model = info.get("model", "")
        tokens_in = info.get("tokens_in", 0)
        tokens_out = info.get("tokens_out", 0)
        response_text = info.get("response", "")

        event = TraceEvent(
            span_id=new_span_id(),
            trace_id=get_current_trace_id(),
            session_id=session_id or get_current_session_id(),
            name=func_name,
            model=str(model),
            prompt=_extract_prompt(kwargs),
            response=str(response_text),
            tokens_in=int(tokens_in),
            tokens_out=int(tokens_out),
            cost_usd=calculate_cost(str(model), int(tokens_in), int(tokens_out)),
            latency_ms=latency_ms,
            error=error,
            tags=tags,
        )
        enqueue_trace(event)
    except Exception:  # noqa: BLE001
        logger.debug("Failed to emit trace event", exc_info=True)


# ---------------------------------------------------------------------------
# Public decorator
# ---------------------------------------------------------------------------


def observe(
    name: Optional[str] = None,
    *,
    session_id: Optional[str] = None,
    tags: Optional[Dict[str, Any]] = None,
) -> Callable:
    """Decorator factory that instruments an LLM-calling function.

    Args:
        name: Override the span name (defaults to the function's ``__name__``).
        session_id: Attach an explicit session ID to every event emitted by
            this function.  If ``None``, the session ID is inherited from the
            enclosing :class:`~llmobs.context.trace` scope (if any).
        tags: Arbitrary key-value metadata merged into every emitted event.

    Returns:
        A decorator that works on both sync and async callables.

    Example::

        @observe(tags={"env": "prod"})
        def summarise(text: str):
            return openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": f"Summarise: {text}"}],
            )

        @observe()
        async def aask(question: str):
            return await openai_async.chat.completions.create(...)
    """
    resolved_tags: Dict[str, Any] = tags or {}

    def decorator(fn: Callable) -> Callable:
        func_name = name or fn.__name__

        if asyncio.iscoroutinefunction(fn):
            @functools.wraps(fn)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                error_msg: Optional[str] = None
                result: Any = None
                t0 = time.perf_counter()
                try:
                    result = await fn(*args, **kwargs)
                    return result
                except Exception as exc:
                    error_msg = f"{type(exc).__name__}: {exc}"
                    raise
                finally:
                    elapsed_ms = int((time.perf_counter() - t0) * 1000)
                    _emit(
                        func_name=func_name,
                        session_id=session_id,
                        tags=resolved_tags,
                        kwargs=kwargs,
                        result=result,
                        latency_ms=elapsed_ms,
                        error=error_msg,
                    )

            return async_wrapper

        @functools.wraps(fn)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            error_msg: Optional[str] = None
            result: Any = None
            t0 = time.perf_counter()
            try:
                result = fn(*args, **kwargs)
                return result
            except Exception as exc:
                error_msg = f"{type(exc).__name__}: {exc}"
                raise
            finally:
                elapsed_ms = int((time.perf_counter() - t0) * 1000)
                _emit(
                    func_name=func_name,
                    session_id=session_id,
                    tags=resolved_tags,
                    kwargs=kwargs,
                    result=result,
                    latency_ms=elapsed_ms,
                    error=error_msg,
                )

        return sync_wrapper

    return decorator
