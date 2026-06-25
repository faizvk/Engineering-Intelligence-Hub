"""Liveness/readiness probe. Returns 200 once the DB pool is reachable, 503
otherwise — every cloud platform's health check hits this.
"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from core.db import engine

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> JSONResponse:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return JSONResponse({"status": "ok"})
    except Exception as exc:  # DB unreachable -> not ready
        return JSONResponse(
            {"status": "degraded", "detail": str(exc)}, status_code=503
        )
