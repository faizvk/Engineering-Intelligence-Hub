# Engineering Intelligence Hub

A production-shaped **RAG** system that ingests an engineering org's scattered
knowledge — technical docs, architecture diagrams, code repositories, and
incident reports — and answers questions with **source-cited, grounded**
responses. The goal is concrete: cut onboarding time and collapse the
rediscovery that inflates MTTR during incidents.

Not a chatbot demo. It exercises the full production surface of an applied-AI
system: hybrid retrieval over pgvector with Voyage embeddings and reranking,
difficulty-based routing across a tiered Claude stack, grounded citations for
trust, a self-correcting LangGraph agent, and a RAGAS/LangSmith evaluation
harness that proves retrieval quality — wired into CI as a quality gate.

## Stack

| Layer | Choice |
| --- | --- |
| Backend | Python 3.11+ · FastAPI · SSE streaming |
| Vector store | Postgres + **pgvector** (HNSW, cosine) |
| Embeddings & rerank | **Voyage AI** — `voyage-3.5` (prose), `voyage-code-3` (code), `rerank-2.5` |
| Generation | **Claude**, tiered — Haiku 4.5 (route) · Sonnet 4.6 (default) · Opus 4.8 (hard) |
| Orchestration | **LangChain (LCEL)** + **LangGraph** (CRAG) |
| Evals & tracing | **RAGAS** + **LangSmith**, gated in CI |
| Frontend | Next.js — flat, minimal, dark chat UI with source pills |
| Infra | Docker · docker-compose · GitHub Actions |

> Anthropic has **no embeddings endpoint** — generation goes to Claude,
> embeddings and reranking go to Voyage. Two keys, kept distinct.

## Architecture

```
                       INGESTION (offline, batch)
  sources ─► loaders ─► source-aware ─► contextualize ─► Voyage embed ─► pgvector
  docs/code/    (md,     chunking       (Haiku +          (voyage-3.5 /   (prose_chunks
  diagrams/     code,    (prose vs       cached doc        voyage-code-3)   code_chunks)
  incidents)    vision,  language-       prefix)                              │
                jira)    aware)                                               │ upsert
                                                                              ▼
                          ┌──────────────────────────────────────────────────────┐
                          │  Postgres + pgvector — HNSW cosine · tsvector (BM25)   │
                          │  acl[] row-level access · metadata jsonb · sha dedup   │
                          └──────────────────────────────────────────────────────┘
                       QUERY (online, streaming)                ▲ search   │ results
  question ─► route ─► [filter+strategy] ─► hybrid ─► rerank ─► assemble ─► Claude ─► SSE
             (Haiku)    (intent → md         (dense    (rerank   (cached     (Sonnet/   tokens +
                         filter; HyDE/        + BM25,   -2.5 →    system +    Opus +     citations
                         multiquery/          RRF)      top-k)    doc blocks) citations) → Next.js
                         decompose)
```

The self-correcting path is a **LangGraph CRAG** state machine:
`route → retrieve → grade_documents → (rewrite ↺ retrieve | generate) →
check_hallucination → (regenerate ↺ | END)`, with both loops bounded.

## Key design decisions

- **pgvector, not a managed vector DB.** Vectors live in the same Postgres as
  metadata and provenance, so an upsert is one transaction and filters are SQL
  `WHERE` clauses. Documented scale ceiling (low-millions of vectors) is the
  migration trigger, not a surprise.
- **Two indexes, one interface.** `voyage-code-3` and `voyage-3.5` occupy
  different vector spaces, so code and prose get separate tables; a router picks
  the index per query and the reranker merges cross-domain results.
- **Retrieve-many, rerank-few.** Hybrid (dense + BM25 via RRF) over-fetches 50
  candidates; a `rerank-2.5` cross-encoder trims to the 6–8 that reach Claude —
  the highest-ROI quality lever.
- **Tiered models.** A Haiku router classifies difficulty; Sonnet handles the
  bulk, Opus only genuinely hard multi-hop reasoning — measurable cost control.
- **Cache the right thing.** The stable system prompt + core docs are
  prompt-cached (~0.1× reads); per-query retrieved chunks are **never** cached
  (pure write cost). Verified via `usage.cache_read_input_tokens`.
- **Citations are the trust mechanism.** Retrieved chunks are passed as Claude
  `document` blocks with `citations` enabled; every claim links back to a span.
  (Citations are incompatible with structured outputs, so the router/graders are
  separate calls.)

## Quickstart

```bash
cp .env.example .env          # fill ANTHROPIC_API_KEY and VOYAGE_API_KEY
make up                       # Postgres + pgvector (+ backend) via docker-compose
make install                  # sync the Python environment (uv, or pip fallback)
make ingest                   # load the demo corpus (data/) into pgvector
make run                      # FastAPI on :8000   ·   POST /query, /query/stream
make test                     # pytest
make eval                     # retrieval metrics + RAGAS quality gate

cd frontend && npm install && npm run dev   # flat-dark chat UI on :3000
```

A small synthetic corpus (handbook docs, a sample repo, two postmortems) ships
under `data/` so the system ingests and demos out of the box.

## Production hardening

Runnable against real private data, not just a demo:

- **Auth + row-level ACLs** — JWT principal; `acl && groups` injected into every
  retrieval query in SQL (default deny); `/admin/costs` gated by an `admin` role;
  ingest jobs/feedback attributed and isolated per user.
- **Secret/PII redaction** at ingestion (emails, provider keys, AWS IDs, JWTs,
  private keys) with a pluggable NER hook.
- **Robustness** — SDK retries/timeouts, `stop_reason` handling (refusal /
  truncation), Opus→Sonnet degradation on 529, hybrid-only fallback if rerank is
  down, and an honest no-answer when retrieval is empty.
- **Freshness** — incremental, content-hash-aware re-indexing with orphan
  cleanup; a cross-source embedding cache; `/ingest` job queue + worker; async +
  Batches contextualization.
- **Ops** — per-user rate limits + daily spend cap; structured logs with a
  `request_id`; Alembic migrations; LangSmith tracing.

## Evaluation

Retrieval and generation are measured as separate stages, because they fail
independently:

- **Retrieval** — deterministic `hit_rate`, `recall@k`, `precision@k`, `MRR`
  over `evals/datasets/golden.jsonl` (12 curated triples). Runs on every commit.
- **Generation** — RAGAS faithfulness, answer relevancy, context
  precision/recall, factual correctness, judged by Claude + Voyage.
- **CI gate** — `python -m evals.run` fails the build under faithfulness 0.85 /
  recall 0.80. LangSmith traces every stage when enabled.

## Project structure

```
core/        # shared kernel: settings, db, schemas, constants, logging, tracing
ingestion/   # offline pipeline: loaders, chunking, embed(+cache), contextualize(+async/batch),
             #   redact, incremental reindex, jobs worker, run CLI
backend/
  api/       # FastAPI routers: health, query (+SSE), ingest, feedback, admin
  rag/       # retrieval (dense/keyword/hybrid/rerank/transform/routing), scoring, LCEL chain, graph/ (CRAG)
  llm/       # Claude client, tier router, cached prompts, citation blocks, answer()
  cost/      # per-request cost meter + spend cap
  security/  # JWT auth, principal, row-level ACL, rate limiting
evals/       # golden set, retrieval metrics, RAGAS, grounding, A/B, CI gate
infra/db/    # canonical pgvector schema + ops tables;  migrations/ (Alembic)
frontend/    # Next.js flat-dark chat UI (citations, cost, feedback)
tests/       # unit + integration
```

## Docs

[`ARCHITECTURE.md`](ARCHITECTURE.md) · [`SECURITY.md`](SECURITY.md) ·
[`WRITEUP.md`](WRITEUP.md) · [`ROADMAP.md`](ROADMAP.md) ·
[`infra/DEPLOY.md`](infra/DEPLOY.md) · [`evals/EXPERIMENTS.md`](evals/EXPERIMENTS.md) ·
[`CHANGELOG.md`](CHANGELOG.md)

## License

MIT © faizvk
