# Build Roadmap

Sequenced as a **thin vertical slice first, then widen** — every phase ends in
something that runs and demos, so there's always a working system to show.

| Phase | Outcome | Status |
|---|---|---|
| 0 | Repo, tooling, secrets, Docker Postgres+pgvector, FastAPI `/health`, green tests | ✅ |
| 1 | Thin vertical slice: docs → cited answer (ingest → embed → pgvector → retrieve → Claude) | ✅ |
| 2 | Voyage `rerank-2.5` two-stage retrieve-then-rerank | ✅ |
| 3 | Code-repo index (`voyage-code-3`, language-aware chunking) | ✅ |
| 4 | Incident reports + hybrid search (BM25 + dense, RRF) | ✅ |
| 5 | Diagrams via Claude vision (describe-then-embed) | ✅ |
| 6 | LangGraph CRAG agent (route → retrieve → grade → generate → check) | ✅ |
| 7 | Evals (RAGAS) + observability (LangSmith) + CI quality gate | ✅ |
| 8 | Prompt caching + tiered model routing + per-query cost meter | ✅ |
| 9 | Multi-stage Docker + docker-compose + GitHub Actions CI | ✅ |
| 10 | Portfolio polish: README, Next.js flat-dark chat UI, this roadmap | ✅ |

## Phase → code map

- **Ingestion & chunking** — `ingestion/` (loaders, source-aware chunking, Voyage
  embeddings, contextual retrieval, redaction).
- **Vector store** — `infra/db/` canonical `prose_chunks` / `code_chunks` schema;
  `backend/rag/vectorstore.py` dense retriever.
- **Retrieval & reranking** — `backend/rag/` hybrid (dense + BM25 RRF), rerank,
  query transforms, intent routing.
- **Generation** — `backend/llm/` tiered Claude, cached prompt, citation blocks,
  streaming `answer()`.
- **Orchestration** — `backend/rag/chain.py` (LCEL), `backend/rag/graph/` (CRAG).
- **Evals & observability** — `evals/` (golden set, retrieval metrics, RAGAS, CI gate).
- **Cost** — `backend/cost/meter.py`.
- **API & frontend** — `backend/api/`, `frontend/`.

## Where I'd go next

- AuthN/Z: JWT principal + per-chunk `acl` enforcement on every retrieval query
  (the `acl` column and ACL predicate are already in the schema/retrievers).
- Incremental, idempotent re-indexing on webhook (content-hash dedup is in place).
- Per-user rate limiting and daily spend caps on the cost meter.
- Scale trigger: migrate to a dedicated vector store only past low-millions of
  vectors — documented, not a surprise.
