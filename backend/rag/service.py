"""Application service: tie retrieval to generation for the API.

answer_query() returns a complete result; stream_query() yields SSE-shaped
events. Streaming runs the (synchronous) Anthropic stream on a worker thread and
drains its tokens onto a queue, so the async endpoint stays non-blocking without
duplicating the generation logic in answer().
"""

from __future__ import annotations

import asyncio
import queue
import threading
from dataclasses import dataclass, field
from typing import AsyncIterator

import anthropic

from backend.llm.answer import answer
from backend.llm.client import DEFAULT_MODEL
from backend.rag.pipeline import docs_to_chunks, retrieve
from backend.rag.scoring import NO_ANSWER
from core.schemas import Citation, Usage


def _answer_with_fallback(question: str, chunks, on_token=None):
    """Generate, degrading Opus->Sonnet on a 529 OverloadedError instead of failing."""
    try:
        return answer(question, chunks, on_token=on_token)
    except anthropic.APIStatusError as e:
        if getattr(e, "status_code", None) == 529:
            return answer(question, chunks, model=DEFAULT_MODEL, on_token=on_token)
        raise


@dataclass
class QueryResult:
    answer: str
    citations: list[Citation] = field(default_factory=list)
    usage: Usage | None = None
    contexts: list[str] = field(default_factory=list)  # for evals


def answer_query(
    question: str,
    *,
    top_k: int = 8,
    acl_groups: list[str] | None = None,
) -> QueryResult:
    docs = retrieve(question, top_k=top_k, acl_groups=acl_groups)
    chunks = docs_to_chunks(docs)
    if not chunks:  # no confident context — don't call Claude, don't hallucinate
        return QueryResult(answer=NO_ANSWER)
    res = _answer_with_fallback(question, chunks)
    return QueryResult(
        answer=res.text,
        citations=res.citations,
        usage=res.usage,
        contexts=[c.text for c in chunks],
    )


_DONE = object()


async def stream_query(
    question: str,
    *,
    top_k: int = 8,
    acl_groups: list[str] | None = None,
) -> AsyncIterator[tuple[str, dict]]:
    """Yield (event, data) pairs: many 'token', then 'sources', then 'usage'."""
    docs = retrieve(question, top_k=top_k, acl_groups=acl_groups)
    chunks = docs_to_chunks(docs)
    if not chunks:  # honest no-answer, no Claude call
        yield ("token", {"text": NO_ANSWER})
        return
    q: queue.Queue = queue.Queue()

    def run() -> None:
        try:
            res = _answer_with_fallback(
                question, chunks, on_token=lambda t: q.put(("token", {"text": t}))
            )
            q.put(("sources", {"citations": [c.model_dump() for c in res.citations]}))
            if res.usage is not None:
                q.put(("usage", res.usage.model_dump()))
        except Exception as exc:  # surface failures as a terminal event
            q.put(("error", {"detail": str(exc)}))
        finally:
            q.put(_DONE)

    threading.Thread(target=run, daemon=True).start()
    loop = asyncio.get_event_loop()
    while True:
        item = await loop.run_in_executor(None, q.get)
        if item is _DONE:
            break
        yield item
