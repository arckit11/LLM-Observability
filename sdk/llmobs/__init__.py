"""LLM Observability SDK — lightweight instrumentation for LLM applications.

Quick start::

    from llmobs import observe, trace

    @observe(tags={"env": "prod"})
    def ask(question: str):
        return openai.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": question}],
        )

    with trace(name="my-pipeline", session_id="user-123"):
        answer = ask("What is LLM observability?")
"""

from __future__ import annotations

from llmobs.context import trace
from llmobs.cost import calculate_cost
from llmobs.decorator import observe
from llmobs.schema import TraceEvent

__version__ = "0.1.0"

__all__ = [
    "ObsClient",
    "TraceEvent",
    "calculate_cost",
    "observe",
    "trace",
]


# ---------------------------------------------------------------------------
# ObsClient — minimal configuration holder
# ---------------------------------------------------------------------------


class ObsClient:
    """Lightweight configuration client for the observability SDK.

    This class provides a central place to override default settings such as
    the Redis connection parameters or global tags that should be attached to
    every trace event.

    Args:
        redis_host: Redis server hostname (overrides ``LLMOBS_REDIS_HOST``).
        redis_port: Redis server port (overrides ``LLMOBS_REDIS_PORT``).
        redis_db: Redis database index (overrides ``LLMOBS_REDIS_DB``).
        redis_password: Redis password (overrides ``LLMOBS_REDIS_PASSWORD``).
        default_tags: Tags merged into every emitted :class:`TraceEvent`.

    Example::

        from llmobs import ObsClient

        client = ObsClient(redis_host="redis.internal", default_tags={"env": "prod"})
    """

    def __init__(
        self,
        *,
        redis_host: str | None = None,
        redis_port: int | None = None,
        redis_db: int | None = None,
        redis_password: str | None = None,
        default_tags: dict | None = None,
    ) -> None:
        import os

        if redis_host is not None:
            os.environ["LLMOBS_REDIS_HOST"] = redis_host
        if redis_port is not None:
            os.environ["LLMOBS_REDIS_PORT"] = str(redis_port)
        if redis_db is not None:
            os.environ["LLMOBS_REDIS_DB"] = str(redis_db)
        if redis_password is not None:
            os.environ["LLMOBS_REDIS_PASSWORD"] = redis_password

        self.default_tags = default_tags or {}

    def __repr__(self) -> str:
        return f"ObsClient(default_tags={self.default_tags!r})"
