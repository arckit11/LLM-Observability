"""Alert engine for the LLM Observability Platform.

Checks incoming spans against three rules:
  1. high_cost_session — session total cost exceeds $0.50
  2. error_spike — error rate in last 5 minutes exceeds 10%
  3. high_latency — single span latency exceeds 5000ms
"""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import CostAlert, TraceSpan

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Threshold constants
# ---------------------------------------------------------------------------
HIGH_COST_SESSION_THRESHOLD = 0.50  # USD
ERROR_SPIKE_THRESHOLD = 0.10  # 10%
ERROR_SPIKE_WINDOW_MINUTES = 5
HIGH_LATENCY_THRESHOLD_MS = 5000


async def get_session_cost(db: AsyncSession, session_id: str) -> float:
    """Return the total cost in USD for a given session."""
    result = await db.execute(
        select(func.coalesce(func.sum(TraceSpan.cost_usd), 0.0)).where(
            TraceSpan.session_id == session_id
        )
    )
    return float(result.scalar_one())


async def get_recent_error_rate(db: AsyncSession, minutes: int = 5) -> float:
    """Return the error rate (0.0–1.0) over the last *minutes* minutes.

    Error rate = spans_with_error / total_spans.  Returns 0.0 when there
    are no recent spans.
    """
    cutoff = datetime.utcnow() - timedelta(minutes=minutes)

    total_result = await db.execute(
        select(func.count(TraceSpan.id)).where(TraceSpan.created_at >= cutoff)
    )
    total = total_result.scalar_one()

    if total == 0:
        return 0.0

    error_result = await db.execute(
        select(func.count(TraceSpan.id)).where(
            TraceSpan.created_at >= cutoff,
            TraceSpan.error.isnot(None),
        )
    )
    errors = error_result.scalar_one()
    return errors / total


async def _already_fired(
    db: AsyncSession, alert_type: str, session_id: str | None, model: str | None
) -> bool:
    """Check if an unresolved alert of this type already exists for the
    given session/model combination to avoid duplicates."""
    stmt = select(CostAlert.id).where(
        CostAlert.alert_type == alert_type,
        CostAlert.resolved.is_(False),
    )
    if session_id is not None:
        stmt = stmt.where(CostAlert.session_id == session_id)
    if model is not None:
        stmt = stmt.where(CostAlert.model == model)
    result = await db.execute(stmt.limit(1))
    return result.first() is not None


async def check_alerts(db: AsyncSession, span: TraceSpan) -> list[CostAlert]:
    """Run all alert rules against the given span.

    Returns a list of newly-created CostAlert objects (may be empty).
    """
    new_alerts: list[CostAlert] = []

    # ---- Rule 1: High-cost session ----------------------------------------
    if span.session_id:
        session_cost = await get_session_cost(db, span.session_id)
        if session_cost > HIGH_COST_SESSION_THRESHOLD:
            if not await _already_fired(db, "high_cost_session", span.session_id, None):
                alert = CostAlert(
                    alert_type="high_cost_session",
                    threshold_value=HIGH_COST_SESSION_THRESHOLD,
                    current_value=session_cost,
                    session_id=span.session_id,
                    message=(
                        f"Session {span.session_id} has accumulated "
                        f"${session_cost:.4f} in cost (threshold: "
                        f"${HIGH_COST_SESSION_THRESHOLD:.2f})."
                    ),
                )
                db.add(alert)
                new_alerts.append(alert)
                logger.warning("Alert fired: high_cost_session for %s", span.session_id)

    # ---- Rule 2: Error spike -----------------------------------------------
    error_rate = await get_recent_error_rate(db, ERROR_SPIKE_WINDOW_MINUTES)
    if error_rate > ERROR_SPIKE_THRESHOLD:
        if not await _already_fired(db, "error_spike", None, None):
            alert = CostAlert(
                alert_type="error_spike",
                threshold_value=ERROR_SPIKE_THRESHOLD,
                current_value=error_rate,
                message=(
                    f"Error rate is {error_rate:.1%} over the last "
                    f"{ERROR_SPIKE_WINDOW_MINUTES} minutes (threshold: "
                    f"{ERROR_SPIKE_THRESHOLD:.0%})."
                ),
            )
            db.add(alert)
            new_alerts.append(alert)
            logger.warning("Alert fired: error_spike (%.1f%%)", error_rate * 100)

    # ---- Rule 3: High latency ---------------------------------------------
    if span.latency_ms > HIGH_LATENCY_THRESHOLD_MS:
        alert = CostAlert(
            alert_type="high_latency",
            threshold_value=float(HIGH_LATENCY_THRESHOLD_MS),
            current_value=float(span.latency_ms),
            model=span.model,
            session_id=span.session_id,
            message=(
                f"Span {span.span_id} ({span.model}) took {span.latency_ms}ms "
                f"(threshold: {HIGH_LATENCY_THRESHOLD_MS}ms)."
            ),
        )
        db.add(alert)
        new_alerts.append(alert)
        logger.warning("Alert fired: high_latency for span %s", span.span_id)

    if new_alerts:
        await db.commit()

    return new_alerts
