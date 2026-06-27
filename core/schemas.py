"""Shared Pydantic domain models used by ingestion, retrieval, generation, and API.

These are the vocabulary the whole system speaks. Keeping them in core/ means
every layer agrees on field names — notably ``source_uri`` and ``doc_type``,
which map 1:1 onto the prose_chunks/code_chunks columns.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class DocType(StrEnum):
    """The four content modalities the Hub ingests. Maps to the doc_type column."""

    DOC = "doc"
    CODE = "code"
    DIAGRAM = "diagram"
    INCIDENT = "incident"


class RetrievedChunk(BaseModel):
    """A chunk returned by retrieval/reranking, ready to become a document block."""

    doc_id: str  # stable identifier, e.g. "incidents/2026-04-12.md#2"
    title: str
    text: str
    source_uri: str
    doc_type: DocType = DocType.DOC
    relevance_score: float | None = None  # set by the reranker
    metadata: dict = Field(default_factory=dict)


class Citation(BaseModel):
    """An inline source-grounded reference returned alongside an answer."""

    quoted_text: str | None = None
    document_title: str | None = None
    doc_id: str | None = None
    source_uri: str | None = None


class Usage(BaseModel):
    """Token accounting for one generation call (the billing ground truth)."""

    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_input_tokens: int = 0
    cache_creation_input_tokens: int = 0
    cost_usd: float | None = None
