"""Voyage embeddings + idempotent upsert into pgvector.

Match the model to the content: voyage-code-3 for code, voyage-3.5 for prose.
Always batch (Voyage accepts many texts per call) and tag input_type
("document" at ingest, "query" at search) — Voyage uses asymmetric encoding.

Upserts are content-hash-aware: a chunk whose content_sha256 is unchanged is
skipped, so re-ingesting a mostly-unchanged corpus only re-embeds what moved.
"""

from __future__ import annotations

import json
import time

import voyageai
from langchain_core.documents import Document

from core.db import raw_connect, vector_literal
from core.schemas import DocType
from core.settings import get_settings
from ingestion.schema import sha256

_settings = get_settings()
_vo = voyageai.Client(api_key=_settings.voyage_api_key.get_secret_value())

# Only these two tables are ever written — a fixed allowlist (no SQL injection).
_TABLES = {"prose_chunks", "code_chunks"}


def embed_batch(
    texts: list[str],
    model: str,
    input_type: str = "document",
    max_batch: int = 128,
) -> list[list[float]]:
    """Embed texts in batches with exponential backoff. Returns L2-normalized vectors."""
    out: list[list[float]] = []
    for i in range(0, len(texts), max_batch):
        chunk = texts[i : i + max_batch]
        for attempt in range(5):
            try:
                resp = _vo.embed(
                    chunk,
                    model=model,
                    input_type=input_type,
                    output_dimension=_settings.embed_dim,  # Matryoshka truncation
                    truncation=True,
                )
                out.extend(resp.embeddings)
                break
            except voyageai.error.RateLimitError:
                time.sleep(2**attempt)
        else:
            raise RuntimeError(f"Voyage failed after retries at batch {i}")
    return out


def embed_and_upsert(chunks: list[Document]) -> int:
    """Route chunks to the right table/model, embed the changed ones, upsert.

    Returns the number of rows written.
    """
    prose = [c for c in chunks if c.metadata.get("doc_type") != DocType.CODE.value]
    code = [c for c in chunks if c.metadata.get("doc_type") == DocType.CODE.value]
    written = 0
    written += _embed_into("prose_chunks", prose, _settings.embed_model)
    written += _embed_into("code_chunks", code, _settings.embed_model_code)
    return written


_UPSERT = """
INSERT INTO {table}
  (content, embedding, doc_type, source_uri, chunk_index,
   repo, language, title, content_sha256, acl, metadata)
VALUES
  (%(content)s, %(embedding)s::vector, %(doc_type)s, %(source_uri)s, %(chunk_index)s,
   %(repo)s, %(language)s, %(title)s, %(sha)s, %(acl)s, %(metadata)s::jsonb)
ON CONFLICT (source_uri, chunk_index) DO UPDATE SET
  content = EXCLUDED.content, embedding = EXCLUDED.embedding, doc_type = EXCLUDED.doc_type,
  repo = EXCLUDED.repo, language = EXCLUDED.language, title = EXCLUDED.title,
  content_sha256 = EXCLUDED.content_sha256, acl = EXCLUDED.acl, metadata = EXCLUDED.metadata
"""


def _embed_into(table: str, chunks: list[Document], model: str) -> int:
    if table not in _TABLES:
        raise ValueError(f"refusing to write to unknown table {table!r}")
    if not chunks:
        return 0

    shas = [sha256(c.page_content) for c in chunks]
    fresh = _unchanged_keys(table, chunks, shas)

    pending = [(c, s) for c, s in zip(chunks, shas) if (c.metadata.get("path"),
               c.metadata.get("chunk_index", 0)) not in fresh]
    if not pending:
        return 0

    vectors = embed_batch([c.page_content for c, _ in pending], model=model)
    with raw_connect() as conn, conn.cursor() as cur:
        for (ch, sha), vec in zip(pending, vectors):
            m = ch.metadata
            cur.execute(
                _UPSERT.format(table=table),
                {
                    "content": ch.page_content,
                    "embedding": vector_literal(vec),
                    "doc_type": m.get("doc_type", DocType.DOC.value),
                    "source_uri": m.get("path", ""),
                    "chunk_index": m.get("chunk_index", 0),
                    "repo": m.get("repo"),
                    "language": m.get("language"),
                    "title": m.get("title"),
                    "sha": sha,
                    "acl": m.get("acl") or ["all"],
                    "metadata": json.dumps(m.get("extra", {})),
                },
            )
        conn.commit()
    return len(pending)


def _unchanged_keys(
    table: str, chunks: list[Document], shas: list[str]
) -> set[tuple[str, int]]:
    """Return (source_uri, chunk_index) keys whose stored sha already matches."""
    sources = sorted({c.metadata.get("path", "") for c in chunks})
    if not sources:
        return set()
    by_key = {
        (c.metadata.get("path", ""), c.metadata.get("chunk_index", 0)): sha
        for c, sha in zip(chunks, shas)
    }
    unchanged: set[tuple[str, int]] = set()
    with raw_connect() as conn, conn.cursor() as cur:
        cur.execute(
            f"SELECT source_uri, chunk_index, content_sha256 FROM {table} "
            "WHERE source_uri = ANY(%s)",
            (sources,),
        )
        for source_uri, chunk_index, stored_sha in cur.fetchall():
            if by_key.get((source_uri, chunk_index)) == stored_sha:
                unchanged.add((source_uri, chunk_index))
    return unchanged
