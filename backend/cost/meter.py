"""Cost model + usage persistence.

The Claude usage object is the billing ground truth. Cache reads bill at ~0.1x
input; the savings come from caching the STABLE prefix (system + core docs) and
NOT the per-query retrieved chunks. Verify caching with cache_hit() — zero reads
on a warm request means a silent invalidator broke the prefix.
"""

from __future__ import annotations

from typing import Any

from core.constants import CACHE_READ_MULT, CACHE_WRITE_MULT, PRICING


def cost_usd(usage: Any) -> float:
    """USD for one generation call. `usage` is any object with the token fields
    and a `.model` (our Usage schema or the raw SDK usage + a model attr)."""
    p = PRICING[usage.model]
    return (
        usage.input_tokens * p["in"] / 1_000_000
        + usage.output_tokens * p["out"] / 1_000_000
        + usage.cache_read_input_tokens * p["in"] * CACHE_READ_MULT / 1_000_000
        + usage.cache_creation_input_tokens * p["in"] * CACHE_WRITE_MULT / 1_000_000
    )


def cache_hit(usage: Any) -> bool:
    """True if the cached prefix was actually read on this request."""
    return getattr(usage, "cache_read_input_tokens", 0) > 0


async def record_usage(db, conversation_id: str | None, usage: Any) -> float | None:
    """Persist a request_costs row and return the computed cost."""
    if usage is None:
        return None
    from sqlalchemy import text

    cost = cost_usd(usage)
    if hasattr(usage, "cost_usd"):
        usage.cost_usd = cost
    await db.execute(
        text(
            """INSERT INTO request_costs
                 (conversation_id, model, input_tokens, output_tokens,
                  cache_read_input_tokens, cache_creation_input_tokens, cost_usd)
               VALUES (:cid, :model, :it, :ot, :crit, :ccit, :cost)"""
        ),
        {
            "cid": conversation_id,
            "model": usage.model,
            "it": usage.input_tokens,
            "ot": usage.output_tokens,
            "crit": usage.cache_read_input_tokens,
            "ccit": usage.cache_creation_input_tokens,
            "cost": cost,
        },
    )
    await db.commit()
    return cost
