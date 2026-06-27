"""Anthropic Contextual Retrieval — context the chunk before embedding.

A raw chunk often loses the context that makes it findable. Before embedding,
prepend a short LLM-generated blurb situating the chunk within its parent doc.
Cost is controlled by prompt caching: the full document is the stable cached
prefix (reused across every chunk in that doc), so only the per-chunk question
varies after the breakpoint — cache reads are ~0.1x input price.

This is offline enrichment and opt-in (`--contextualize`): it costs Haiku-tier
tokens, so the vertical slice runs fine without it.
"""

from __future__ import annotations

from collections import defaultdict

import anthropic
from langchain_core.documents import Document

from core.settings import get_settings

_settings = get_settings()
_client = anthropic.Anthropic(api_key=_settings.anthropic_api_key.get_secret_value())

CONTEXT_PROMPT = (
    "Here is a chunk from the document above. Give a short (1-2 sentence) context "
    "that situates this chunk within the overall document, to improve search "
    "retrieval. Answer ONLY with the context, nothing else.\n\n"
    "<chunk>\n{chunk}\n</chunk>"
)


def contextualize_doc(full_document: str, chunks: list[Document]) -> list[Document]:
    """Prepend an LLM context blurb to each chunk of ONE source document.

    The full document is the cached prefix; only the per-chunk question varies,
    so every chunk after the first is served from cache at ~0.1x input price.
    """
    out: list[Document] = []
    for ch in chunks:
        resp = _client.messages.create(
            model=_settings.model_router,  # cheap; the task is mechanical
            max_tokens=150,
            system=[
                {
                    "type": "text",
                    "text": f"<document>\n{full_document}\n</document>",
                    "cache_control": {"type": "ephemeral"},  # the whole win
                }
            ],
            messages=[{"role": "user", "content": CONTEXT_PROMPT.format(chunk=ch.page_content)}],
        )
        blurb = next(b.text for b in resp.content if b.type == "text")
        ch.page_content = f"{blurb}\n\n{ch.page_content}"  # embed blurb + chunk
        ch.metadata["context_blurb"] = blurb
        out.append(ch)
    return out


def contextualize_all(parent_text: dict[str, str], chunks: list[Document]) -> list[Document]:
    """Group chunks by parent path, then contextualize each group."""
    by_parent: dict[str, list[Document]] = defaultdict(list)
    for ch in chunks:
        by_parent[ch.metadata["path"]].append(ch)
    result: list[Document] = []
    for path, group in by_parent.items():
        result.extend(contextualize_doc(parent_text.get(path, ""), group))
    return result
