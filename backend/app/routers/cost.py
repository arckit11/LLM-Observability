"""Cost analytics API endpoints."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import TraceSpan
from app.db.session import get_db

router = APIRouter(prefix="/cost", tags=["cost"])


@router.get("/summary")
async def cost_summary(
    db: AsyncSession = Depends(get_db),
    from_dt: Optional[datetime] = Query(None),
    to_dt: Optional[datetime] = Query(None),
):
    """Per-model cost breakdown: total cost, call count, avg cost, total tokens."""
    stmt = select(
        TraceSpan.model,
        func.sum(TraceSpan.cost_usd).label("total_cost"),
        func.count(TraceSpan.id).label("call_count"),
        func.avg(TraceSpan.cost_usd).label("avg_cost_per_call"),
        func.sum(TraceSpan.tokens_in + TraceSpan.tokens_out).label("total_tokens"),
    )

    if from_dt:
        stmt = stmt.where(TraceSpan.created_at >= from_dt)
    if to_dt:
        stmt = stmt.where(TraceSpan.created_at <= to_dt)

    stmt = stmt.group_by(TraceSpan.model).order_by(func.sum(TraceSpan.cost_usd).desc())

    result = await db.execute(stmt)
    rows = result.all()

    return [
        {
            "model": row.model,
            "total_cost": float(row.total_cost or 0),
            "call_count": row.call_count,
            "avg_cost_per_call": float(row.avg_cost_per_call or 0),
            "total_tokens": int(row.total_tokens or 0),
        }
        for row in rows
    ]


@router.get("/timeseries")
async def cost_timeseries(
    db: AsyncSession = Depends(get_db),
    from_dt: Optional[datetime] = Query(None),
    to_dt: Optional[datetime] = Query(None),
    interval: str = Query("hour", regex="^(hour|day)$"),
):
    """Hourly or daily cost aggregation using PostgreSQL date_trunc."""
    trunc_expr = func.date_trunc(interval, TraceSpan.created_at)

    stmt = select(
        trunc_expr.label("bucket"),
        func.sum(TraceSpan.cost_usd).label("total_cost"),
        func.count(TraceSpan.id).label("call_count"),
        func.sum(TraceSpan.tokens_in + TraceSpan.tokens_out).label("total_tokens"),
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
            "cost_usd": float(row.total_cost or 0),
            "call_count": row.call_count,
            "total_tokens": int(row.total_tokens or 0),
        }
        for row in rows
    ]
