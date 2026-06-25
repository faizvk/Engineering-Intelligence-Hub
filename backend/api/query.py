"""Query endpoints: non-streaming JSON and SSE token streaming.

Both return source-grounded citations. Handlers are thin — validate, hand off to
the RAG service, stream or return.
"""

from __future__ import annotations

import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.rag.service import answer_query, stream_query
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
async def query(req: QueryRequest) -> QueryResponse:
    result = answer_query(req.question)
    return QueryResponse(
        answer=result.answer, citations=result.citations, usage=result.usage
    )


@router.post("/stream")
async def query_stream(req: QueryRequest) -> StreamingResponse:
    async def event_source():
        async for event, data in stream_query(req.question):
            yield _sse(event, data)
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
