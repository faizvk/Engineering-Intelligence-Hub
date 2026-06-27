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
from ingestion.loaders import code, diagrams, docs, incidents, pdf

DATA = Path("data")


def load_sources() -> list[Document]:
    raw: list[Document] = []
    handbook = DATA / "handbook"
    if handbook.exists():
        raw += docs.load_markdown_tree(str(handbook), source="handbook")
    repo = DATA / "repo"
    if repo.exists():
        raw += code.load_local_code(str(repo), repo="platform")
    jira = DATA / "incidents" / "jira_export.json"
    if jira.exists():
        raw += incidents.load_jira_incidents(str(jira))
    diagram_dir = DATA / "diagrams"
    images = [str(p) for ext in ("*.png", "*.jpg", "*.jpeg") for p in diagram_dir.glob(ext)]
    if images:
        raw += diagrams.load_diagrams(images, source="diagrams")
    pdfs = [str(p) for p in DATA.rglob("*.pdf")]
    if pdfs:
        raw += pdf.load_pdfs(pdfs)
    return raw


def ingest(contextualize: bool = False, concurrent: bool = False) -> int:
    raw = load_sources()
    if not raw:
        print("No sources found under ./data — nothing to ingest.")
        return 0

    # Parent text map for contextualization (diagrams/incidents are self-contained).
    parent_text = {d.metadata["path"]: d.page_content for d in raw}

    chunks = split_documents(raw)
    if contextualize:
        if concurrent:
            from ingestion.contextualize_async import contextualize_all_concurrent

            chunks = contextualize_all_concurrent(parent_text, chunks)
        else:
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
    ap.add_argument(
        "--concurrent",
        action="store_true",
        help="Contextualize concurrently (bounded asyncio) instead of serially.",
    )
    args = ap.parse_args()
    ingest(contextualize=args.contextualize, concurrent=args.concurrent)


if __name__ == "__main__":
    main()
