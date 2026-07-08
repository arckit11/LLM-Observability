"""Non-blocking Redis Streams writer for trace events.

Design principles:
  * **Fire-and-forget** — writes are dispatched on daemon threads and must
    never block the caller's hot path.
  * **Silent failure** — all Redis and serialisation errors are swallowed so
    that observability tooling can never crash the user's application.
  * **Lazy initialisation** — the Redis connection is created on first use
    and reused as a module-level singleton.

Configuration is read from environment variables:

* ``LLMOBS_REDIS_HOST`` (default ``localhost``)
* ``LLMOBS_REDIS_PORT`` (default ``6379``)
* ``LLMOBS_REDIS_DB``   (default ``0``)
* ``LLMOBS_REDIS_PASSWORD`` (default ``None``)

The target Redis stream is ``llmobs:traces`` with a capped length of 50 000
entries to prevent unbounded memory growth.
"""

from __future__ import annotations

import logging
import os
import threading
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    import redis

    from llmobs.schema import TraceEvent

logger = logging.getLogger("llmobs.queue")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

STREAM_KEY: str = "llmobs:traces"
STREAM_MAXLEN: int = 50_000

# ---------------------------------------------------------------------------
# Lazy singleton Redis connection
# ---------------------------------------------------------------------------

_redis_client: Optional["redis.Redis"] = None
_client_lock = threading.Lock()


def _get_redis_client() -> "redis.Redis":
    """Return (and lazily create) the module-level Redis client."""
    global _redis_client  # noqa: PLW0603

    if _redis_client is not None:
        return _redis_client

    with _client_lock:
        # Double-checked locking
        if _redis_client is not None:
            return _redis_client

        import redis as _redis_mod

        _redis_client = _redis_mod.Redis(
            host=os.getenv("LLMOBS_REDIS_HOST", "localhost"),
            port=int(os.getenv("LLMOBS_REDIS_PORT", "6379")),
            db=int(os.getenv("LLMOBS_REDIS_DB", "0")),
            password=os.getenv("LLMOBS_REDIS_PASSWORD") or None,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
        )
        return _redis_client


# ---------------------------------------------------------------------------
# Internal writer (runs on daemon thread)
# ---------------------------------------------------------------------------


def _write_event(event: "TraceEvent") -> None:
    """Serialise and XADD the event — called on a background thread."""
    try:
        client = _get_redis_client()
        payload = {"data": event.model_dump_json()}
        client.xadd(STREAM_KEY, payload, maxlen=STREAM_MAXLEN, approximate=True)
    except Exception:  # noqa: BLE001
        logger.debug("Failed to write trace event to Redis", exc_info=True)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def enqueue_trace(event: "TraceEvent") -> None:
    """Enqueue a :class:`~llmobs.schema.TraceEvent` for async delivery.

    The event is serialised and written to the ``llmobs:traces`` Redis stream
    on a daemon thread so that the caller is never blocked.

    Args:
        event: The trace event to enqueue.

    Note:
        All exceptions (connection errors, serialisation errors, etc.) are
        silently caught and logged at DEBUG level.
    """
    try:
        thread = threading.Thread(target=_write_event, args=(event,), daemon=True)
        thread.start()
    except Exception:  # noqa: BLE001
        logger.debug("Failed to spawn trace writer thread", exc_info=True)
