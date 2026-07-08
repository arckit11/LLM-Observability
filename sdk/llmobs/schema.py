"""Pydantic v2 schema definitions for LLM observability trace events.

This module defines the core data model used throughout the SDK to represent
a single observed LLM interaction span.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    """Return the current UTC datetime (timezone-aware)."""
    return datetime.now(timezone.utc)


class TraceEvent(BaseModel):
    """A single observed LLM interaction span.

    Attributes:
        span_id: Unique identifier for this individual span (short hex string).
        trace_id: Identifier grouping related spans into a single trace.
        session_id: Optional higher-level session grouping (e.g. a chat thread).
        name: Human-readable label for this span (e.g. the decorated function name).
        model: The LLM model identifier used for this call.
        prompt: The input prompt or serialised messages sent to the model.
        response: The raw text response returned by the model.
        tokens_in: Number of input / prompt tokens consumed.
        tokens_out: Number of output / completion tokens generated.
        cost_usd: Estimated cost of this call in US dollars.
        latency_ms: Wall-clock latency of the call in milliseconds.
        error: Error message if the call failed, otherwise ``None``.
        tags: Arbitrary key-value metadata attached by the caller.
        timestamp: UTC timestamp when the event was recorded.
    """

    span_id: str = Field(..., description="Unique span identifier (short hex).")
    trace_id: str = Field(..., description="Trace identifier grouping related spans.")
    session_id: Optional[str] = Field(
        default=None, description="Optional session / thread identifier."
    )
    name: str = Field(..., description="Human-readable span label.")
    model: str = Field(default="", description="LLM model identifier.")
    prompt: str = Field(default="", description="Input prompt or serialised messages.")
    response: str = Field(default="", description="Raw model response text.")
    tokens_in: int = Field(default=0, ge=0, description="Input token count.")
    tokens_out: int = Field(default=0, ge=0, description="Output token count.")
    cost_usd: float = Field(default=0.0, ge=0.0, description="Estimated cost (USD).")
    latency_ms: int = Field(default=0, ge=0, description="Latency in milliseconds.")
    error: Optional[str] = Field(
        default=None, description="Error message on failure."
    )
    tags: Dict[str, Any] = Field(
        default_factory=dict, description="Arbitrary metadata tags."
    )
    timestamp: datetime = Field(
        default_factory=_utcnow,
        description="UTC timestamp when the event was recorded.",
    )

    model_config = {
        "json_encoders": {datetime: lambda v: v.isoformat()},
        "populate_by_name": True,
    }
