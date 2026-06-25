"""Incremental, idempotent re-indexing.

Re-embedding everything is wasteful; re-embedding nothing makes answers stale.
embed_and_upsert() already re-embeds only chunks whose content_sha256 changed
(see embed.py). This adds the other half: delete chunks that vanished from a
source (a file shrank or was removed), so a re-index of one source converges to
exactly its current chunks. Webhook-driven (a repo push / new incident hits
/ingest) re-indexes just that source — no full rebuild.

Heavy deps (DB driver, Voyage) are imported lazily so the pure orphans() helper
stays importable (and unit-testable) without them.
"""

from __future__ import annotations

from collections import defaultdict

from core.schemas import DocType

_TABLES = {"prose_chunks", "code_chunks"}


def orphans(existing_indexes: set[int], incoming_indexes: set[int]) -> set[int]:
    """chunk_index values present in the store but no longer in the source."""
    return set(existing_indexes) - set(incoming_indexes)


def _table_for(chunk) -> str:
    code = chunk.metadata.get("doc_type") == DocType.CODE.value
    return "code_chunks" if code else "prose_chunks"


def reindex(new_chunks: list) -> int:
    """Upsert changed chunks (sha-aware) and delete vanished ones. Returns #upserted."""
    from ingestion.embed import embed_and_upsert

    written = embed_and_upsert(new_chunks)
    _delete_orphans(new_chunks)
    return written


def _delete_orphans(new_chunks: list) -> None:
    from core.db import raw_connect

    keep: dict[tuple[str, str], set[int]] = defaultdict(set)  # (table, source_uri) -> indexes
    for c in new_chunks:
        keep[(_table_for(c), c.metadata["path"])].add(c.metadata.get("chunk_index", 0))
    with raw_connect() as conn, conn.cursor() as cur:
        for (table, source_uri), indexes in keep.items():
            if table not in _TABLES:
                continue
            cur.execute(
                f"DELETE FROM {table} WHERE source_uri = %s AND NOT (chunk_index = ANY(%s))",
                (source_uri, list(indexes)),
            )
        conn.commit()
