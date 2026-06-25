# Changelog

## v0.2 — Production hardening

Turns the demo into something runnable against real private data.

- **Security**: JWT auth + `Principal`; row-level ACL (`acl && groups`) enforced
  in SQL on every retrieval path; endpoint RBAC for `/admin/costs`; per-user
  isolation of ingest jobs and feedback; deeper secret/PII redaction with an NER
  hook; per-user rate limits + daily spend cap.
- **Robustness**: explicit retries/timeouts, `stop_reason` handling, Opus→Sonnet
  degradation on overload, hybrid-only fallback when rerank is down, score floor
  + honest no-answer short-circuit.
- **Freshness**: incremental idempotent re-indexing with orphan cleanup;
  cross-source embedding cache; async + Batches contextualization; PDF loader;
  `/ingest` job queue + worker.
- **Ops**: structured JSON logs with a `request_id`; `@traceable` spans; Alembic
  migrations; multi-turn `conversation_id` on the serving path; `/admin/costs`.
- **Evals/tests**: deterministic citation-grounding check; A/B harness +
  `EXPERIMENTS.md`; golden set expanded to 18 with per-category MRR; more unit
  tests (filter compiler, hybrid keying, router tier, SSE, dim contract).
- **DX/Deploy**: pre-commit + Dependabot; Fly.io + Render config + deploy guide;
  frontend feedback/cost/error states; ARCHITECTURE/SECURITY/WRITEUP docs.

## v0.1 — Phases 0–10

Full RAG pipeline from scratch: scaffold + pgvector schema; ingestion (docs,
code, incidents, diagrams) with source-aware chunking and Voyage embeddings;
hybrid retrieval + RRF + Voyage reranking + query transforms; tiered Claude
generation with cached prompts and grounded citations; LCEL + a self-correcting
LangGraph CRAG agent; RAGAS + LangSmith + a CI quality gate; per-request cost
meter; Docker + GitHub Actions; a flat-dark Next.js chat UI.
