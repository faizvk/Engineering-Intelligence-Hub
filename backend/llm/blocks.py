"""Citation-enabled document blocks, and structural parsing of the citations
Claude returns. Kept free of the anthropic import so the mapping is unit-testable.

Each retrieved chunk becomes a `document` block with citations enabled; Claude
then returns inline citation objects pointing back to the exact source span. We
map each citation's document_index back to the chunk to recover doc_id/source_uri.
Never regex the prose — parse citations structurally.
"""

from __future__ import annotations

import base64
import mimetypes
import pathlib
from typing import Any

from core.schemas import Citation, DocType, RetrievedChunk


def to_document_blocks(chunks: list[RetrievedChunk]) -> list[dict]:
    """Turn reranked retrieval results into citation-enabled document blocks.

    These are per-query and therefore NEVER given cache_control — they change
    every request, so caching them is pure write cost with zero reads.
    """
    blocks: list[dict] = []
    for c in chunks:
        blocks.append(
            {
                "type": "document",
                "source": {"type": "text", "media_type": "text/plain", "data": c.text},
                "title": c.title,
                # context is metadata for the model, not cited text — good for the id/uri.
                "context": f"source_id={c.doc_id} uri={c.source_uri}",
                "citations": {"enabled": True},
            }
        )
    return blocks


def to_image_blocks(chunks: list[RetrievedChunk]) -> list[dict]:
    """For diagram chunks whose original image is on disk, attach the image so
    Claude can reason over the actual diagram (not just its transcribed text).

    Only fires for DocType.DIAGRAM with a readable image_path; otherwise empty.
    """
    blocks: list[dict] = []
    for c in chunks:
        if c.doc_type != DocType.DIAGRAM:
            continue
        path = c.metadata.get("image_path")
        if not path or not pathlib.Path(path).is_file():
            continue
        media_type, _ = mimetypes.guess_type(path)
        data = base64.standard_b64encode(pathlib.Path(path).read_bytes()).decode()
        blocks.append(
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type or "image/png",
                    "data": data,
                },
            }
        )
    return blocks


def extract_citations(content_block: Any, chunks: list[RetrievedChunk]) -> list[Citation]:
    """Map each inline citation on a text block back to its originating chunk."""
    out: list[Citation] = []
    for cit in getattr(content_block, "citations", None) or []:
        idx = getattr(cit, "document_index", None)
        src = chunks[idx] if isinstance(idx, int) and 0 <= idx < len(chunks) else None
        out.append(
            Citation(
                quoted_text=getattr(cit, "cited_text", None),
                document_title=getattr(cit, "document_title", None),
                doc_id=src.doc_id if src else None,
                source_uri=src.source_uri if src else None,
            )
        )
    return out
