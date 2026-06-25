"""A single chunk-metadata shape for every source.

Everything funnels into one metadata dict so retrieval, filtering, and citation
rendering are uniform regardless of origin. The keys map 1:1 onto the
prose_chunks/code_chunks columns and the JSONB metadata blob. DocType is the
canonical enum from core — defined once, reused here.
"""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from core.schemas import DocType

__all__ = ["DocType", "ChunkMetadata", "utcnow_iso", "sha256"]


@dataclass
class ChunkMetadata:
    source: str  # logical source name, e.g. "confluence:Platform"
    path: str  # file path, URL, or repo-relative path -> source_uri
    doc_type: DocType
    repo: str | None = None
    language: str | None = None  # for code chunks: "python", "go", ...
    author: str | None = None
    created_at: str | None = None  # ISO 8601
    title: str | None = None
    chunk_index: int = 0
    acl: list[str] = field(default_factory=list)  # groups allowed to see this chunk
    extra: dict[str, Any] = field(default_factory=dict)  # severity, ticket id, ...

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["doc_type"] = self.doc_type.value
        return d


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(text: str) -> str:
    """Content hash for idempotent re-indexing and embed caching."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
