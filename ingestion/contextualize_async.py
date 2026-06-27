"""Concurrent contextualization with a bounded semaphore.

The per-chunk Claude call is the slow part of ingestion. Running them with a
bounded asyncio.gather makes a backfill take minutes, not hours, while staying
under rate limits. Each call still rides the Haiku-tier prompt cache (the
document prefix is cached once, ~0.1x reads thereafter). For a one-time backfill
prefer the Batches API (-50%); use this for incremental re-ingests where you
want results immediately.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict

import anthropic

from core.settings import get_settings
from ingestion.contextualize import CONTEXT_PROMPT

_s = get_settings()
_aclient = anthropic.AsyncAnthropic(api_key=_s.anthropic_api_key.get_secret_value(), max_retries=3)
_SEM = asyncio.Semaphore(8)  # bound concurrency to stay under rate limits


async def _ctx_one(full_doc: str, chunk):
    async with _SEM:
        resp = await _aclient.messages.create(
            model=_s.model_router,
            max_tokens=150,
            system=[
                {
                    "type": "text",
                    "text": f"<document>\n{full_doc}\n</document>",
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": CONTEXT_PROMPT.format(chunk=chunk.page_content)}],
        )
    blurb = next(b.text for b in resp.content if b.type == "text")
    chunk.page_content = f"{blurb}\n\n{chunk.page_content}"
    chunk.metadata["context_blurb"] = blurb
    return chunk


async def contextualize_all_async(parent_text: dict[str, str], chunks: list) -> list:
    by_parent: dict[str, list] = defaultdict(list)
    for ch in chunks:
        by_parent[ch.metadata["path"]].append(ch)
    tasks = [
        _ctx_one(parent_text.get(path, ""), c) for path, group in by_parent.items() for c in group
    ]
    return list(await asyncio.gather(*tasks))


def contextualize_all_concurrent(parent_text: dict[str, str], chunks: list) -> list:
    """Sync entrypoint for the ingestion CLI."""
    return asyncio.run(contextualize_all_async(parent_text, chunks))
