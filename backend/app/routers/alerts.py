"""Alert management API endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import CostAlert
from app.db.session import get_db

router = APIRouter(prefix="/alerts", tags=["alerts"])


def _alert_to_dict(alert: CostAlert) -> dict:
    """Convert a CostAlert ORM object to a JSON-serializable dict."""
    return {
        "id": alert.id,
        "alert_type": alert.alert_type,
        "threshold_value": alert.threshold_value,
        "current_value": alert.current_value,
        "session_id": alert.session_id,
        "model": alert.model,
        "message": alert.message,
        "fired_at": alert.fired_at.isoformat() if alert.fired_at else None,
        "resolved": alert.resolved,
    }


@router.get("")
async def list_alerts(
    db: AsyncSession = Depends(get_db),
    resolved: Optional[bool] = Query(None),
    alert_type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """List alerts with optional filters."""
    stmt = select(CostAlert)

    if resolved is not None:
        stmt = stmt.where(CostAlert.resolved == resolved)
    if alert_type:
        stmt = stmt.where(CostAlert.alert_type == alert_type)

    stmt = stmt.order_by(CostAlert.fired_at.desc()).limit(limit).offset(offset)

    result = await db.execute(stmt)
    alerts = result.scalars().all()

    return [_alert_to_dict(a) for a in alerts]


@router.post("/{alert_id}/resolve")
async def resolve_alert(alert_id: int, db: AsyncSession = Depends(get_db)):
    """Mark an alert as resolved."""
    result = await db.execute(
        select(CostAlert).where(CostAlert.id == alert_id)
    )
    alert = result.scalar_one_or_none()

    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found")

    if alert.resolved:
        return {"message": "Alert already resolved", "alert": _alert_to_dict(alert)}

    alert.resolved = True
    await db.commit()
    await db.refresh(alert)

    return {"message": "Alert resolved", "alert": _alert_to_dict(alert)}
