"""SQLAlchemy 2.0 ORM models for LLM Observability Platform."""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""
    pass


class TraceSpan(Base):
    """Represents a single span within an LLM trace.

    Each span captures one LLM call including prompt, response, token counts,
    cost, latency, and optional error information.
    """

    __tablename__ = "trace_spans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    span_id: Mapped[str] = mapped_column(String(8), index=True, nullable=False)
    trace_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    session_id: Mapped[str | None] = mapped_column(String(100), index=True, nullable=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False, default="")
    response: Mapped[str] = mapped_column(Text, nullable=False, default="")
    tokens_in: Mapped[int] = mapped_column(Integer, default=0)
    tokens_out: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), index=True
    )


class CostAlert(Base):
    """Represents an alert fired by the alert engine.

    Alerts are triggered when cost, error rate, or latency thresholds
    are exceeded. They can be resolved via the API.
    """

    __tablename__ = "cost_alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    alert_type: Mapped[str] = mapped_column(String(50), nullable=False)
    threshold_value: Mapped[float] = mapped_column(Float, nullable=False)
    current_value: Mapped[float] = mapped_column(Float, nullable=False)
    session_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    fired_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
