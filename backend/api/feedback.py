"""Capture thumbs up/down against an answer — the cheapest high-value signal,
feeding the eval flywheel (downvoted runs become new golden-set cases).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text

from backend.security.auth import current_principal
from backend.security.principal import Principal
from core.db import get_db

router = APIRouter(prefix="/feedback", tags=["feedback"])


class FeedbackRequest(BaseModel):
    answer_id: str | None = None
    run_id: str | None = None  # LangSmith run id
    rating: int  # +1 / -1
    reason: str | None = None


@router.post("", status_code=201)
async def feedback(
    req: FeedbackRequest,
    db=Depends(get_db),
    p: Principal = Depends(current_principal),
) -> dict:
    await db.execute(
        text(
            """INSERT INTO feedback (answer_id, run_id, rating, reason)
               VALUES (:a, :r, :rating, :reason)"""
        ),
        {"a": req.answer_id, "r": req.run_id, "rating": req.rating, "reason": req.reason},
    )
    await db.commit()
    return {"status": "recorded"}
