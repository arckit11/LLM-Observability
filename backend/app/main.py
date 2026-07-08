"""FastAPI application entry point for the LLM Observability Platform."""

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.consumer import consume_forever
from app.db.models import Base, TraceSpan
from app.db.session import engine, get_db
from app.routers import alerts, cost, latency, traces

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan: create tables + start Redis consumer
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler.

    On startup:
      1. Create database tables if they don't exist.
      2. Launch the Redis Streams consumer as a background task.

    On shutdown:
      1. Cancel the consumer task.
      2. Dispose of the SQLAlchemy engine.
    """
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created / verified.")

    # Start consumer
    consumer_task = asyncio.create_task(consume_forever(engine))
    logger.info("Redis consumer background task started.")

    yield

    # Shutdown
    consumer_task.cancel()
    try:
        await consumer_task
    except asyncio.CancelledError:
        pass
    await engine.dispose()
    logger.info("Shutdown complete.")


# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
app = FastAPI(
    title="LLM Observability Platform",
    description="Backend API for monitoring LLM usage, costs, latency, and alerts.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow all origins for dashboard access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers under /api prefix
app.include_router(traces.router, prefix="/api")
app.include_router(cost.router, prefix="/api")
app.include_router(latency.router, prefix="/api")
app.include_router(alerts.router, prefix="/api")


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.get("/health", tags=["health"])
async def health_check():
    """Simple health check endpoint."""
    return {"status": "healthy", "service": "llm-observability-backend"}


# ---------------------------------------------------------------------------
# Stats overview
# ---------------------------------------------------------------------------
@app.get("/api/stats/overview", tags=["stats"])
async def stats_overview(
    db: AsyncSession = Depends(get_db),
    hours: int = Query(24, ge=1, le=720),
):
    """Dashboard overview stats.

    Returns aggregate metrics including total spans, cost, active sessions,
    error rate, average latency, spans today, and top models.
    """
    # Total spans
    total_spans_result = await db.execute(select(func.count(TraceSpan.id)))
    total_spans = total_spans_result.scalar_one()

    # Total cost
    total_cost_result = await db.execute(
        select(func.coalesce(func.sum(TraceSpan.cost_usd), 0.0))
    )
    total_cost = float(total_cost_result.scalar_one())

    # Active sessions (distinct session_ids)
    active_sessions_result = await db.execute(
        select(func.count(func.distinct(TraceSpan.session_id))).where(
            TraceSpan.session_id.isnot(None)
        )
    )
    active_sessions = active_sessions_result.scalar_one()

    # Error rate (overall)
    if total_spans > 0:
        error_count_result = await db.execute(
            select(func.count(TraceSpan.id)).where(TraceSpan.error.isnot(None))
        )
        error_count = error_count_result.scalar_one()
        error_rate = error_count / total_spans
    else:
        error_rate = 0.0

    # Average latency
    avg_latency_result = await db.execute(
        select(func.coalesce(func.avg(TraceSpan.latency_ms), 0.0))
    )
    avg_latency = float(avg_latency_result.scalar_one())

    # Spans today (last 24h from now)
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    spans_today_result = await db.execute(
        select(func.count(TraceSpan.id)).where(TraceSpan.created_at >= cutoff)
    )
    spans_today = spans_today_result.scalar_one()

    # Top models by call count
    top_models_result = await db.execute(
        select(
            TraceSpan.model,
            func.count(TraceSpan.id).label("call_count"),
            func.coalesce(func.sum(TraceSpan.cost_usd), 0.0).label("total_cost"),
        )
        .group_by(TraceSpan.model)
        .order_by(func.count(TraceSpan.id).desc())
        .limit(10)
    )
    top_models = [
        {
            "model": row.model,
            "call_count": row.call_count,
            "total_cost": float(row.total_cost),
        }
        for row in top_models_result.all()
    ]

    # Recent traces (last 10 spans)
    recent_stmt = (
        select(TraceSpan)
        .order_by(TraceSpan.created_at.desc())
        .limit(10)
    )
    recent_result = await db.execute(recent_stmt)
    recent_spans = recent_result.scalars().all()
    recent_traces = [
        {
            "trace_id": s.trace_id,
            "name": s.name,
            "model": s.model,
            "latency_ms": s.latency_ms,
            "cost_usd": s.cost_usd,
            "error": s.error,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }
        for s in recent_spans
    ]

    # Cost trend (hourly for last 24h)
    trend_cutoff = datetime.utcnow() - timedelta(hours=24)
    trend_stmt = (
        select(
            func.date_trunc("hour", TraceSpan.created_at).label("hour"),
            func.coalesce(func.sum(TraceSpan.cost_usd), 0.0).label("cost_usd"),
        )
        .where(TraceSpan.created_at >= trend_cutoff)
        .group_by(text("1"))
        .order_by(text("1"))
    )
    trend_result = await db.execute(trend_stmt)
    cost_trend = [
        {
            "hour": row.hour.strftime("%I:%M %p") if row.hour else None,
            "cost_usd": float(row.cost_usd),
        }
        for row in trend_result.all()
    ]

    return {
        "total_spans": total_spans,
        "total_cost": total_cost,
        "active_sessions": active_sessions,
        "error_rate": round(error_rate, 4),
        "avg_latency": round(avg_latency, 2),
        "spans_today": spans_today,
        "top_models": top_models,
        "recent_traces": recent_traces,
        "cost_trend": cost_trend,
    }
