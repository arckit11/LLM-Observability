"""Latency analytics API endpoints."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import TraceSpan
from app.db.session import get_db

router = APIRouter(prefix="/latency", tags=["latency"])


@router.get("/percentiles")
async def latency_percentiles(
    db: AsyncSession = Depends(get_db),
    model: Optional[str] = Query(None),
    hours: int = Query(24, ge=1, le=720),
):
    """P50, P95, P99 latency percentiles per model.

    Uses PostgreSQL's ``percentile_cont`` ordered-set aggregate via raw SQL
    because SQLAlchemy's ORM doesn't natively support ordered-set aggregates.
    """
    model_filter = ""
    params: dict = {"hours": hours}

    if model:
        model_filter = "AND model = :model"
        params["model"] = model

    query = text(f"""
        SELECT
            model,
            percentile_cont(0.50) WITHIN GROUP (ORDER BY latency_ms) AS p50,
            percentile_cont(0.95) WITHIN GROUP (ORDER BY latency_ms) AS p95,
            percentile_cont(0.99) WITHIN GROUP (ORDER BY latency_ms) AS p99,
            avg(latency_ms) AS avg_latency,
            count(*) AS sample_count
        FROM trace_spans
        WHERE created_at >= now() - make_interval(hours => :hours)
            {model_filter}
        GROUP BY model
        ORDER BY model
    """)

    result = await db.execute(query, params)
    rows = result.all()

    return [
        {
            "model": row.model,
            "p50": float(row.p50) if row.p50 is not None else None,
            "p95": float(row.p95) if row.p95 is not None else None,
            "p99": float(row.p99) if row.p99 is not None else None,
            "avg_latency": float(row.avg_latency) if row.avg_latency is not None else None,
            "sample_count": row.sample_count,
        }
        for row in rows
    ]


@router.get("/timeseries")
async def latency_timeseries(
    db: AsyncSession = Depends(get_db),
    from_dt: Optional[datetime] = Query(None),
    to_dt: Optional[datetime] = Query(None),
    interval: str = Query("hour", regex="^(hour|day)$"),
):
    """Hourly or daily latency trends: avg latency and P95 over time."""
    trunc_expr = func.date_trunc(interval, TraceSpan.created_at)

    # Use raw SQL for percentile_cont within the ORM-built query
    p95_sql = text(
        "percentile_cont(0.95) WITHIN GROUP (ORDER BY trace_spans.latency_ms)"
    )

    stmt = select(
        trunc_expr.label("bucket"),
        func.avg(TraceSpan.latency_ms).label("avg_latency"),
        p95_sql.label("p95_latency"),
        func.count(TraceSpan.id).label("sample_count"),
    )

    if from_dt:
        stmt = stmt.where(TraceSpan.created_at >= from_dt)
    if to_dt:
        stmt = stmt.where(TraceSpan.created_at <= to_dt)

    stmt = stmt.group_by(text("1")).order_by(text("1"))

    result = await db.execute(stmt)
    rows = result.all()

    return [
        {
            "hour": row.bucket.isoformat() if row.bucket else None,
            "latency_ms": float(row.avg_latency) if row.avg_latency is not None else None,
            "p95_latency": float(row.p95_latency) if row.p95_latency is not None else None,
            "sample_count": row.sample_count,
        }
        for row in rows
    ]
