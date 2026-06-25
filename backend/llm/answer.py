"""The full answer() function: tiered model, cached prefix, citation document
blocks, adaptive thinking on the hard path, and streaming.

Streaming is the default — RAG answers can be long, and a non-streaming request
with a large max_tokens risks an SDK HTTP timeout. We pull the assembled message
with get_final_message() to parse citations and verify the cache afterward.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from backend.llm.blocks import extract_citations, to_document_blocks
from backend.llm.client import HARD_MODEL, client
from backend.llm.prompts import CORE_CONTEXT, SYSTEM_PROMPT
from backend.llm.router import route
from core.schemas import Citation, RetrievedChunk, Usage


@dataclass
class AnswerResult:
    text: str = ""
    citations: list[Citation] = field(default_factory=list)
    model: str = ""
    usage: Usage | None = None


def thinking_config(model: str) -> dict:
    """Adaptive thinking + high effort on the hard path; off and cheap otherwise.

    NO budget_tokens (removed on 4.x — 400s). NO temperature/top_p/top_k. Steer
    with the prompt and output_config.effort.
    """
    if model == HARD_MODEL:  # claude-opus-4-8
        return {
            "thinking": {"type": "adaptive", "display": "summarized"},
            "output_config": {"effort": "xhigh"},
        }
    return {  # Sonnet workhorse — answer directly, keep it cheap/fast
        "thinking": {"type": "disabled"},
        "output_config": {"effort": "low"},
    }


def answer(
    question: str,
    chunks: list[RetrievedChunk],
    *,
    model: str | None = None,
    on_token=None,  # optional callback(str) for streaming to a UI / SSE
) -> AnswerResult:
    """Generate a grounded, cited answer from reranked retrieval results."""
    model = model or route(question)
    cfg = thinking_config(model)

    # System prompt + stable core docs = the CACHED prefix.
    system = [
        {"type": "text", "text": SYSTEM_PROMPT},
        {
            "type": "text",
            "text": CORE_CONTEXT,
            "cache_control": {"type": "ephemeral"},  # prefix breakpoint
        },
    ]

    # Per-query content: retrieved chunks (NOT cached) + the question, LAST.
    user_content = to_document_blocks(chunks) + [
        {"type": "text", "text": f"Question: {question}"}
    ]

    # Generous on the hard path so multi-hop answers don't truncate mid-thought.
    max_tokens = 16000 if model == HARD_MODEL else 4096

    result = AnswerResult(model=model)
    with client.messages.stream(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user_content}],
        **cfg,
    ) as stream:
        for text in stream.text_stream:  # token deltas
            result.text += text
            if on_token:
                on_token(text)
        final = stream.get_final_message()

    for block in final.content:
        if block.type == "text":
            result.citations.extend(extract_citations(block, chunks))

    u = final.usage
    result.usage = Usage(
        model=model,
        input_tokens=u.input_tokens,
        output_tokens=u.output_tokens,
        cache_read_input_tokens=getattr(u, "cache_read_input_tokens", 0) or 0,
        cache_creation_input_tokens=getattr(u, "cache_creation_input_tokens", 0) or 0,
    )
    return result
