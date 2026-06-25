"""Ingestion worker: drain queued ingest_jobs (enqueued by the API).

Each job becomes a redacted Document, is chunked source-aware, and re-indexed
idempotently. Run as a one-shot or a loop: `python -m ingestion.jobs`.
"""

from __future__ import annotations

from langchain_core.documents import Document

from core.db import raw_connect
from core.schemas import DocType
from ingestion.chunking import split_documents
from ingestion.incremental import reindex
from ingestion.redact import redact
from ingestion.schema import ChunkMetadata, utcnow_iso


def process_pending(limit: int = 50) -> int:
    """Process up to `limit` queued jobs. Returns the number processed."""
    with raw_connect() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT id, source_uri, doc_type, content, acl FROM ingest_jobs "
            "WHERE status = 'queued' ORDER BY id LIMIT %s FOR UPDATE SKIP LOCKED",
            (limit,),
        )
        jobs = cur.fetchall()
        ids = [j[0] for j in jobs]
        if ids:
            cur.execute(
                "UPDATE ingest_jobs SET status = 'processing' WHERE id = ANY(%s)", (ids,)
            )
        conn.commit()

    for job_id, source_uri, doc_type, content, acl in jobs:
        try:
            doc = Document(
                page_content=redact(content),
                metadata=ChunkMetadata(
                    source="api",
                    path=source_uri,
                    doc_type=DocType(doc_type),
                    created_at=utcnow_iso(),
                    acl=list(acl) if acl else ["all"],
                ).to_dict(),
            )
            reindex(split_documents([doc]))
            _mark(job_id, "done")
        except Exception as exc:  # noqa: BLE001 — record and continue
            _mark(job_id, "error", str(exc))
    return len(jobs)


def _mark(job_id: int, status: str, error: str | None = None) -> None:
    with raw_connect() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE ingest_jobs SET status = %s, error = %s, processed_at = now() WHERE id = %s",
            (status, error, job_id),
        )
        conn.commit()


if __name__ == "__main__":
    n = process_pending()
    print(f"Processed {n} ingest job(s).")
