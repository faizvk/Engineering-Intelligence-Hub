"""Ingestion entrypoint: load per source -> split source-aware -> (optionally)
contextualize -> embed + upsert into pgvector.

Sources are wired in as their loaders land across the build phases. Run with::

    python -m ingestion.run                 # docs only, no LLM enrichment
    python -m ingestion.run --contextualize  # + Anthropic Contextual Retrieval
"""

from __future__ import annotations

import argparse
from pathlib import Path

from langchain_core.documents import Document

from ingestion.chunking import split_documents
from ingestion.embed import embed_and_upsert
from ingestion.loaders import docs

DATA = Path("data")


def load_sources() -> list[Document]:
    raw: list[Document] = []
    handbook = DATA / "handbook"
    if handbook.exists():
        raw += docs.load_markdown_tree(str(handbook), source="handbook")
    # Code, incidents, and diagrams loaders are wired here as later phases add them.
    return raw


def ingest(contextualize: bool = False) -> int:
    raw = load_sources()
    if not raw:
        print("No sources found under ./data — nothing to ingest.")
        return 0

    # Parent text map for contextualization (diagrams/incidents are self-contained).
    parent_text = {d.metadata["path"]: d.page_content for d in raw}

    chunks = split_documents(raw)
    if contextualize:
        from ingestion.contextualize import contextualize_all

        chunks = contextualize_all(parent_text, chunks)

    n = embed_and_upsert(chunks)
    print(f"Ingested {len(raw)} source docs -> {len(chunks)} chunks -> upserted {n}.")
    return n


def main() -> None:
    ap = argparse.ArgumentParser(description="Engineering Intelligence Hub ingestion")
    ap.add_argument(
        "--contextualize",
        action="store_true",
        help="Prepend Anthropic Contextual Retrieval blurbs before embedding (costs Haiku tokens).",
    )
    args = ap.parse_args()
    ingest(contextualize=args.contextualize)


if __name__ == "__main__":
    main()
