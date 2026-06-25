"""Per-principal rate limiting + daily spend cap.

Every /query fans out to Haiku + Voyage embed + Voyage rerank + Sonnet/Opus, so
an unthrottled caller can run a large bill. The limiter keys on the authenticated
user (falling back to client IP), and the spend cap reads the cost ledger.
"""

from __future__ import annotations

from fastapi import HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address

from backend.cost.meter import daily_spend
from core.settings import get_settings


def _key(request: Request) -> str:
    principal = getattr(request.state, "principal", None)
    return getattr(principal, "user_id", None) or get_remote_address(request)


limiter = Limiter(key_func=_key)


def per_minute_limit() -> str:
    return f"{get_settings().rate_limit_per_minute}/minute"


async def enforce_spend_cap(db, user_id: str) -> None:
    cap = get_settings().daily_spend_cap_usd
    if await daily_spend(db, user_id) >= cap:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS, f"daily spend cap (${cap}) reached"
        )
