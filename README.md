# Engineering Intelligence Hub

A developer-focused **RAG** (Retrieval-Augmented Generation) system that ingests
technical docs, architecture diagrams, code repositories, and incident reports,
and answers engineering questions with **source-cited, grounded** responses — to
accelerate onboarding and cut troubleshooting time.

> Status: building in public, phase by phase. See [`ROADMAP.md`](ROADMAP.md).

## Stack

| Layer | Choice |
| --- | --- |
| Backend | Python 3.11+ · FastAPI · SSE streaming |
| Vector store | Postgres + **pgvector** (HNSW) |
| Embeddings & rerank | **Voyage AI** (`voyage-3.5`, `voyage-code-3`, `rerank-2.5`) |
| Generation | **Claude** — tiered: Haiku 4.5 (routing) · Sonnet 4.6 (default) · Opus 4.8 (hard) |
| Orchestration | **LangChain (LCEL)** + **LangGraph** |
| Evals & tracing | **RAGAS** + **LangSmith** |
| Frontend | Next.js — flat, minimal, dark chat UI |
| Infra | Docker · docker-compose · GitHub Actions |

## Quickstart

```bash
cp .env.example .env        # then fill ANTHROPIC_API_KEY and VOYAGE_API_KEY
make up                     # Postgres + pgvector via docker-compose
make install                # sync the Python environment
make ingest                 # load the demo corpus into pgvector
make run                    # FastAPI backend on :8000
```

Anthropic has **no embeddings endpoint** — generation goes to Claude, embeddings
and reranking go to Voyage. Keep the two keys distinct.

## License

MIT © faizvk
