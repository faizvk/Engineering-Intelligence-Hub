"""PDF docs (runbooks, design docs, reports) via pypdf.

Extract text per page into one Document per file (chunked later as prose),
redacting before anything is embedded. Image-only/diagram PDFs are better routed
through the vision loader; this is for text PDFs.
"""

from __future__ import annotations

from pathlib import Path

from langchain_core.documents import Document
from pypdf import PdfReader

from ingestion.redact import redact
from ingestion.schema import ChunkMetadata, DocType, utcnow_iso


def load_pdfs(
    paths: list[str], source: str = "pdfs", acl: list[str] | None = None
) -> list[Document]:
    docs: list[Document] = []
    for p in paths:
        reader = PdfReader(p)
        text = "\n\n".join((page.extract_text() or "") for page in reader.pages)
        if not text.strip():
            continue  # likely an image-only PDF — use the vision loader instead
        docs.append(
            Document(
                page_content=redact(text),
                metadata=ChunkMetadata(
                    source=source,
                    path=p,
                    doc_type=DocType.DOC,
                    title=Path(p).stem,
                    created_at=utcnow_iso(),
                    acl=acl or ["all"],
                ).to_dict(),
            )
        )
    return docs
