"""Trace-related API endpoints."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import TraceSpan
from app.db.session import get_db

router = APIRouter(prefix="/traces", tags=["traces"])


def _span_to_dict(span: TraceSpan) -> dict:
    """Convert a TraceSpan ORM object to a JSON-serializable dict."""
    return {
        "id": span.id,
        "span_id": span.span_id,
        "trace_id": span.trace_id,
        "session_id": span.session_id,
        "name": span.name,
        "model": span.model,
        "prompt": span.prompt,
        "response": span.response,
        "tokens_in": span.tokens_in,
        "tokens_out": span.tokens_out,
        "cost_usd": span.cost_usd,
        "latency_ms": span.latency_ms,
        "error": span.error,
        "tags": span.tags,
        "created_at": span.created_at.isoformat() if span.created_at else None,
    }


# --------------------------------------------------------------------------
# GET /traces/sessions  (MUST be before /traces/{trace_id})
# --------------------------------------------------------------------------
@router.get("/sessions")
async def list_sessions(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Return distinct session IDs with span count and total cost."""
    stmt = (
        select(
            TraceSpan.session_id,
            func.count(TraceSpan.id).label("span_count"),
            func.coalesce(func.sum(TraceSpan.cost_usd), 0.0).label("total_cost"),
            func.min(TraceSpan.created_at).label("first_seen"),
            func.max(TraceSpan.created_at).label("last_seen"),
        )
        .where(TraceSpan.session_id.isnot(None))
        .group_by(TraceSpan.session_id)
        .order_by(func.max(TraceSpan.created_at).desc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(stmt)
    rows = result.all()

    return [
        {
            "session_id": row.session_id,
            "span_count": row.span_count,
            "total_cost": float(row.total_cost),
            "first_seen": row.first_seen.isoformat() if row.first_seen else None,
            "last_seen": row.last_seen.isoformat() if row.last_seen else None,
        }
        for row in rows
    ]


# --------------------------------------------------------------------------
# GET /traces/{trace_id}
# --------------------------------------------------------------------------
@router.get("/{trace_id}")
async def get_trace(trace_id: str, db: AsyncSession = Depends(get_db)):
    """Return all spans for a given trace, ordered by created_at."""
    stmt = (
        select(TraceSpan)
        .where(TraceSpan.trace_id == trace_id)
        .order_by(TraceSpan.created_at)
    )
    result = await db.execute(stmt)
    spans = result.scalars().all()

    if not spans:
        raise HTTPException(status_code=404, detail="Trace not found")

    return [_span_to_dict(s) for s in spans]


# --------------------------------------------------------------------------
# GET /traces
# --------------------------------------------------------------------------
@router.get("")
async def list_traces(
    db: AsyncSession = Depends(get_db),
    session_id: Optional[str] = Query(None),
    model: Optional[str] = Query(None),
    from_dt: Optional[datetime] = Query(None),
    to_dt: Optional[datetime] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Paginated list of spans with optional filters."""
    stmt = select(TraceSpan)

    if session_id:
        stmt = stmt.where(TraceSpan.session_id == session_id)
    if model:
        stmt = stmt.where(TraceSpan.model == model)
    if from_dt:
        stmt = stmt.where(TraceSpan.created_at >= from_dt)
    if to_dt:
        stmt = stmt.where(TraceSpan.created_at <= to_dt)

    # Get total count for pagination metadata
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar_one()

    stmt = stmt.order_by(TraceSpan.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(stmt)
    spans = result.scalars().all()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "data": [_span_to_dict(s) for s in spans],
    }
