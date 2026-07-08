"""Token-to-cost calculator for popular LLM models.

Pricing is expressed in **USD per token** (not per 1K or 1M tokens) so that
``calculate_cost`` can simply multiply counts without further scaling.

Pricing data is approximate and based on publicly listed rates as of mid-2025.
Update the ``PRICING`` dict when providers change their rates.
"""

from __future__ import annotations

from typing import Dict, Tuple

# ---------------------------------------------------------------------------
# Pricing table: model -> (input_cost_per_token, output_cost_per_token)
# ---------------------------------------------------------------------------

PRICING: Dict[str, Tuple[float, float]] = {
    # OpenAI -----------------------------------------------------------
    "gpt-4o":           (2.50e-06, 10.00e-06),
    "gpt-4o-mini":      (0.15e-06,  0.60e-06),
    "gpt-4-turbo":      (10.00e-06, 30.00e-06),
    "gpt-3.5-turbo":    (0.50e-06,  1.50e-06),
    # Anthropic --------------------------------------------------------
    "claude-3-5-sonnet": (3.00e-06, 15.00e-06),
    "claude-3-haiku":    (0.25e-06,  1.25e-06),
    "claude-3-opus":     (15.00e-06, 75.00e-06),
    # Google -----------------------------------------------------------
    "gemini-1.5-pro":    (1.25e-06,  5.00e-06),
    "gemini-1.5-flash":  (0.075e-06, 0.30e-06),
    "gemini-2.0-flash":  (0.10e-06,  0.40e-06),
    # Open-source (hosted estimates) -----------------------------------
    "llama3":            (0.05e-06,  0.08e-06),
    "mixtral":           (0.24e-06,  0.24e-06),
}


def calculate_cost(model: str, tokens_in: int, tokens_out: int) -> float:
    """Estimate the USD cost for a single LLM call.

    Args:
        model: Model identifier (must match a key in :data:`PRICING`).
               A case-insensitive prefix match is attempted if the exact key
               is not found (e.g. ``"gpt-4o-2024-08-06"`` matches ``"gpt-4o"``).
        tokens_in: Number of input / prompt tokens.
        tokens_out: Number of output / completion tokens.

    Returns:
        Estimated cost in USD.  Returns ``0.0`` for unknown models so that
        observability never breaks the application.
    """
    price = _resolve_pricing(model)
    if price is None:
        return 0.0
    input_cost, output_cost = price
    return (tokens_in * input_cost) + (tokens_out * output_cost)


def _resolve_pricing(model: str) -> Tuple[float, float] | None:
    """Resolve pricing by exact match first, then by prefix match."""
    key = model.strip().lower()

    # Exact match
    if key in PRICING:
        return PRICING[key]

    # Prefix / substring match (e.g. "gpt-4o-2024-08-06" -> "gpt-4o")
    # Sort candidates longest-first so more specific keys win.
    for candidate in sorted(PRICING, key=len, reverse=True):
        if key.startswith(candidate):
            return PRICING[candidate]

    return None
