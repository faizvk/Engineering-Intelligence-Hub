"""Query endpoints: non-streaming JSON and SSE token streaming.

Both return source-grounded citations. Handlers are thin — validate, hand off to
the RAG service, stream or return.
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.cost.meter import record_usage
from backend.rag.service import answer_query, stream_query
from backend.security.auth import current_principal
from backend.security.principal import Principal
from backend.security.ratelimit import enforce_spend_cap, limiter, per_minute_limit
from core.db import get_db
from core.schemas import Citation, Usage

router = APIRouter(prefix="/query", tags=["query"])


class QueryRequest(BaseModel):
    question: str
    conversation_id: str | None = None


class QueryResponse(BaseModel):
    answer: str
    citations: list[Citation]
    usage: Usage | None = None


@router.post("", response_model=QueryResponse)
@limiter.limit(per_minute_limit)
async def query(
    request: Request,
    req: QueryRequest,
    db=Depends(get_db),
    p: Principal = Depends(current_principal),
) -> QueryResponse:
    await enforce_spend_cap(db, p.user_id)
    # acl_groups come from the authenticated principal, NEVER from the request body.
    result = answer_query(
        req.question, conversation_id=req.conversation_id, acl_groups=p.groups
    )
    await record_usage(db, req.conversation_id, result.usage, user_id=p.user_id)
    return QueryResponse(
        answer=result.answer, citations=result.citations, usage=result.usage
    )


@router.post("/stream")
@limiter.limit(per_minute_limit)
async def query_stream(
    request: Request,
    req: QueryRequest,
    db=Depends(get_db),
    p: Principal = Depends(current_principal),
) -> StreamingResponse:
    await enforce_spend_cap(db, p.user_id)

    async def event_source():
        captured_usage: dict | None = None
        async for event, data in stream_query(
            req.question, conversation_id=req.conversation_id, acl_groups=p.groups
        ):
            if event == "usage":
                captured_usage = data
            yield _sse(event, data)
        # Persist usage the same way the non-streaming path does (consistent metrics).
        if captured_usage:
            try:
                await record_usage(
                    db, req.conversation_id, Usage(**captured_usage), user_id=p.user_id
                )
            except Exception:
                pass
        yield _sse("done", {})

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # disable proxy buffering so tokens flush
        },
    )


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"
