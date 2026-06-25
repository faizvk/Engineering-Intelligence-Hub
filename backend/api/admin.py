"""Operational cost rollup. Surfaces the request_costs ledger so spend is
visible (today's total, per-model split, and a 14-day trend for a dashboard).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text

from backend.security.auth import current_principal
from backend.security.principal import Principal
from core.db import get_db

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/costs")
async def costs(db=Depends(get_db), p: Principal = Depends(current_principal)) -> dict:
    today = (
        await db.execute(
            text(
                "SELECT COALESCE(SUM(cost_usd), 0), COUNT(*) FROM request_costs "
                "WHERE created_at >= date_trunc('day', now())"
            )
        )
    ).first()
    per_model = (
        await db.execute(
            text(
                "SELECT model, COUNT(*), COALESCE(SUM(cost_usd), 0) FROM request_costs "
                "GROUP BY model ORDER BY 3 DESC"
            )
        )
    ).all()
    daily = (
        await db.execute(
            text(
                "SELECT date_trunc('day', created_at)::date AS d, COALESCE(SUM(cost_usd), 0) "
                "FROM request_costs WHERE created_at >= now() - interval '14 days' "
                "GROUP BY d ORDER BY d"
            )
        )
    ).all()
    return {
        "today": {"cost_usd": float(today[0]), "queries": today[1]},
        "per_model": [{"model": m, "queries": n, "cost_usd": float(c)} for m, n, c in per_model],
        "daily": [{"day": str(d), "cost_usd": float(c)} for d, c in daily],
    }
