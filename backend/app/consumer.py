"""Redis Streams consumer for ingesting trace spans.

Reads serialized span data from a Redis stream named 'llm:traces',
deserializes the JSON payloads, bulk-inserts them into PostgreSQL,
and runs the alert engine on each span.
"""

import asyncio
import json
import logging
import os

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, AsyncSession

from app.alerting import check_alerts
from app.db.models import TraceSpan

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
STREAM_KEY = os.getenv("REDIS_STREAM_KEY", "llmobs:traces")
GROUP_NAME = "backend-workers"
CONSUMER_NAME = os.getenv("HOSTNAME", "consumer-1")
BATCH_SIZE = 100
BLOCK_MS = 1000  # 1-second block


def _parse_span_data(raw: dict[bytes | str, bytes | str]) -> dict:
    """Extract and deserialise the span payload from a stream entry.

    The producer is expected to place a JSON blob under the ``data`` key.
    If ``data`` is missing, the raw dict values are decoded and used directly.
    """
    decoded = {
        (k.decode() if isinstance(k, bytes) else k): (
            v.decode() if isinstance(v, bytes) else v
        )
        for k, v in raw.items()
    }

    if "data" in decoded:
        return json.loads(decoded["data"])
    return decoded


async def _ensure_consumer_group(r: aioredis.Redis) -> None:
    """Create the consumer group if it doesn't already exist."""
    try:
        await r.xgroup_create(STREAM_KEY, GROUP_NAME, id="0", mkstream=True)
        logger.info("Created consumer group '%s' on stream '%s'", GROUP_NAME, STREAM_KEY)
    except aioredis.ResponseError as exc:
        if "BUSYGROUP" in str(exc):
            logger.debug("Consumer group '%s' already exists.", GROUP_NAME)
        else:
            raise


async def consume_forever(engine: AsyncEngine) -> None:
    """Run the main consumer loop.

    Connects to Redis, ensures the consumer group exists, and continuously
    reads batches of messages.  Each batch is bulk-inserted into PostgreSQL
    and then acknowledged.
    """
    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    r = aioredis.from_url(REDIS_URL, decode_responses=False)
    await _ensure_consumer_group(r)

    logger.info(
        "Consumer '%s' started — reading from '%s' (group '%s')",
        CONSUMER_NAME,
        STREAM_KEY,
        GROUP_NAME,
    )

    while True:
        try:
            messages = await r.xreadgroup(
                GROUP_NAME,
                CONSUMER_NAME,
                {STREAM_KEY: ">"},
                count=BATCH_SIZE,
                block=BLOCK_MS,
            )

            if not messages:
                continue

            async with session_factory() as db:
                message_ids: list[bytes | str] = []

                for _stream, entries in messages:
                    for msg_id, fields in entries:
                        message_ids.append(msg_id)
                        try:
                            data = _parse_span_data(fields)
                            span = TraceSpan(
                                span_id=data.get("span_id", ""),
                                trace_id=data.get("trace_id", ""),
                                session_id=data.get("session_id"),
                                name=data.get("name", "unknown"),
                                model=data.get("model", "unknown"),
                                prompt=data.get("prompt", ""),
                                response=data.get("response", ""),
                                tokens_in=int(data.get("tokens_in", 0)),
                                tokens_out=int(data.get("tokens_out", 0)),
                                cost_usd=float(data.get("cost_usd", 0.0)),
                                latency_ms=int(data.get("latency_ms", 0)),
                                error=data.get("error"),
                                tags=data.get("tags", {}),
                            )
                            db.add(span)
                            await db.flush()  # ensure span.id is populated
                            await check_alerts(db, span)
                        except Exception:
                            logger.exception(
                                "Failed to process message %s", msg_id
                            )

                await db.commit()

                # ACK all processed messages in one call
                if message_ids:
                    await r.xack(STREAM_KEY, GROUP_NAME, *message_ids)
                    logger.debug("ACKed %d messages", len(message_ids))

        except asyncio.CancelledError:
            logger.info("Consumer shutting down.")
            break
        except Exception:
            logger.exception("Consumer error — retrying in 5s")
            await asyncio.sleep(5)

    await r.aclose()
