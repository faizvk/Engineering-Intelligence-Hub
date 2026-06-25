"""Bulk contextualization via the Batches API (-50%).

Contextual Retrieval is offline and latency-tolerant, so the one-time corpus
backfill belongs in a batch: submit all the Haiku calls and get 50% off on top of
the prompt-cache savings. Combined stack: Batches (-50%) x cache reads (~0.1x) on
a Haiku-tier model — corpus enrichment for cents.

Use the sync/async paths for incremental ingest; use this for the backfill.
"""

from __future__ import annotations

import time

import anthropic
from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
from anthropic.types.messages.batch_create_params import Request

from core.settings import get_settings
from ingestion.contextualize import CONTEXT_PROMPT

_s = get_settings()
_client = anthropic.Anthropic(api_key=_s.anthropic_api_key.get_secret_value())


def submit_context_batch(jobs: list[tuple[str, str, str]]):
    """jobs: list of (chunk_id, full_document, chunk_text). Returns the batch."""
    requests = [
        Request(
            custom_id=chunk_id,
            params=MessageCreateParamsNonStreaming(
                model=_s.model_router,
                max_tokens=150,
                system=[
                    {
                        "type": "text",
                        "text": f"<document>\n{full_doc}\n</document>",
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=[
                    {"role": "user", "content": CONTEXT_PROMPT.format(chunk=chunk_text)}
                ],
            ),
        )
        for (chunk_id, full_doc, chunk_text) in jobs
    ]
    return _client.messages.batches.create(requests=requests)


def fetch_blurbs(batch_id: str, poll_seconds: int = 30) -> dict[str, str]:
    """Poll until the batch ends, then map custom_id -> context blurb."""
    while _client.messages.batches.retrieve(batch_id).processing_status != "ended":
        time.sleep(poll_seconds)
    out: dict[str, str] = {}
    for result in _client.messages.batches.results(batch_id):
        if result.result.type == "succeeded":
            msg = result.result.message
            out[result.custom_id] = next(b.text for b in msg.content if b.type == "text")
    return out
