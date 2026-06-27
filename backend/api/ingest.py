"""Ingest endpoint: enqueue a document for the ingestion worker, return 202.

Heavy work (chunk + embed + upsert) does not belong on the request path, and the
API must not import the ingestion pipeline (layering). So we write a job row and
return immediately; `python -m ingestion.jobs` drains the queue.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text

from backend.security.auth import current_principal
from backend.security.principal import Principal
from core.db import get_db

router = APIRouter(prefix="/ingest", tags=["ingest"])


class IngestRequest(BaseModel):
    source_uri: str
    doc_type: str  # "doc" | "code" | "incident" | "diagram"
    content: str
    acl: list[str] | None = None


@router.post("", status_code=202)
async def ingest(
    req: IngestRequest, db=Depends(get_db), p: Principal = Depends(current_principal)
) -> dict:
    row = await db.execute(
        text(
            """INSERT INTO ingest_jobs (source_uri, doc_type, content, user_id, acl)
               VALUES (:uri, :dt, :content, :uid, :acl) RETURNING id"""
        ),
        {
            "uri": req.source_uri,
            "dt": req.doc_type,
            "content": req.content,
            "uid": p.user_id,
            "acl": req.acl or ["all"],
        },
    )
    job_id = row.scalar()
    await db.commit()
    return {"job_id": job_id, "status": "queued"}


@router.get("/{job_id}")
async def job_status(
    job_id: int, db=Depends(get_db), p: Principal = Depends(current_principal)
) -> dict:
    # Only the job's owner can see its status (and error text).
    row = await db.execute(
        text("SELECT status, error FROM ingest_jobs WHERE id = :i AND user_id = :u"),
        {"i": job_id, "u": p.user_id},
    )
    r = row.first()
    if r is None:
        raise HTTPException(404, "job not found")
    return {"job_id": job_id, "status": r[0], "error": r[1]}
