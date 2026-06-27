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
from collections.abc import AsyncIterator
from dataclasses import dataclass, field

import anthropic

from backend.cost.meter import cost_usd
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


def _resolve(conversation_id: str | None, question: str):
    """For a follow-up, condense history + question into a standalone query so
    retrieval isn't confused by pronouns. Returns (standalone_query, history_obj)."""
    if not conversation_id:
        return question, None
    from backend.rag.chain import condense_q, get_history

    history = get_history(conversation_id)
    msgs = history.messages
    standalone = condense_q.invoke({"history": msgs, "question": question}) if msgs else question
    return standalone, history


def _persist(history, question: str, answer_text: str) -> None:
    if history is not None:
        history.add_user_message(question)
        history.add_ai_message(answer_text)


@dataclass
class QueryResult:
    answer: str
    citations: list[Citation] = field(default_factory=list)
    usage: Usage | None = None
    contexts: list[str] = field(default_factory=list)  # for evals


def answer_query(
    question: str,
    *,
    conversation_id: str | None = None,
    top_k: int = 8,
    acl_groups: list[str] | None = None,
) -> QueryResult:
    standalone, history = _resolve(conversation_id, question)
    docs = retrieve(standalone, top_k=top_k, acl_groups=acl_groups)
    chunks = docs_to_chunks(docs)
    if not chunks:  # no confident context — don't call Claude, don't hallucinate
        _persist(history, question, NO_ANSWER)
        return QueryResult(answer=NO_ANSWER)
    res = _answer_with_fallback(standalone, chunks)
    _persist(history, question, res.text)
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
    conversation_id: str | None = None,
    top_k: int = 8,
    acl_groups: list[str] | None = None,
) -> AsyncIterator[tuple[str, dict]]:
    """Yield (event, data) pairs: many 'token', then 'sources', then 'usage'."""
    standalone, history = _resolve(conversation_id, question)
    docs = retrieve(standalone, top_k=top_k, acl_groups=acl_groups)
    chunks = docs_to_chunks(docs)
    if not chunks:  # honest no-answer, no Claude call
        _persist(history, question, NO_ANSWER)
        yield ("token", {"text": NO_ANSWER})
        return
    q: queue.Queue = queue.Queue()

    def run() -> None:
        try:
            res = _answer_with_fallback(
                standalone, chunks, on_token=lambda t: q.put(("token", {"text": t}))
            )
            _persist(history, question, res.text)
            q.put(("sources", {"citations": [c.model_dump() for c in res.citations]}))
            if res.usage is not None:
                res.usage.cost_usd = cost_usd(res.usage)  # so the UI can show it
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
