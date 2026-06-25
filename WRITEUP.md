# Building the Engineering Intelligence Hub

A write-up of what this system is, the decisions that shaped it, and how to talk
about them.

## The problem

Engineering knowledge is real but non-retrievable: stale across three wikis,
encoded in code no doc captured, locked in diagram images, buried in postmortems
that already solved today's incident. Keyword search fails because the question
and the answer rarely share vocabulary — someone asks "why do payments retry
twice" and the answer is a postmortem titled "INC-4412: duplicate charge."

## The shape of the solution

A retrieval pipeline that ingests heterogeneous sources into one schema, retrieves
with a hybrid (dense + lexical) strategy then reranks, routes across a tiered
Claude stack by difficulty, and grounds every answer in inline citations — all
measured by an eval harness wired into CI.

The hard parts were not calling the model. They were: chunking heterogeneous
sources well, getting *precision* out of retrieval, controlling cost, and being
able to *measure* whether a change actually helped.

## Decisions worth defending

- **pgvector, not a managed vector DB.** Co-locating vectors with relational
  metadata collapsed a distributed write-consistency problem into one
  transaction. I documented the scale ceiling (low-millions of vectors) as the
  migration trigger — choosing, not defaulting.
- **A cross-encoder reranker is the highest-ROI lever.** The embedding model is a
  bi-encoder (query and doc encoded independently — scales, but can't model
  interaction). The reranker reads the pair jointly. Retrieve 50, rerank to 8;
  the biggest answer-quality jump for the least code.
- **Hybrid retrieval with RRF.** Dense misses exact identifiers
  (`ConnectionPoolTimeout`, `PROD-4821`); BM25 catches them. RRF fuses on rank, so
  the two score scales never have to align.
- **Tiered models as cost engineering.** A Haiku router classifies difficulty;
  Sonnet handles ~80%, Opus only the genuinely hard. The routing call runs on the
  cheapest model, and the tier split is instrumented so the threshold is tuned
  against eval scores, not vibes.
- **Cache the stable prefix, never the retrieved chunks.** The system prompt +
  core docs are prompt-cached (~0.1× reads); per-query chunks change every request
  so caching them is pure write cost. Verified via `cache_read_input_tokens`.
- **Citations are the trust mechanism.** `document` blocks with citations enabled
  make every claim traceable. I also added a *deterministic* grounding check: the
  cited span must appear verbatim in the retrieved context.
- **LangGraph for the self-correcting loop.** Corrective RAG (grade → rewrite →
  retry → generate → hallucination-check) is a stateful graph with cycles, not a
  linear chain — and the loops are bounded so they can't run away.

## What makes it production-shaped

Auth + row-level ACLs enforced in SQL on every retrieval path; secret redaction
at ingestion; rate limits + spend caps; SDK retries + `stop_reason` handling +
Opus→Sonnet degradation on overload; an honest no-answer when retrieval is empty;
incremental, content-hash-aware re-indexing; structured logs with a request_id;
Alembic migrations; and a CI quality gate that fails the build if faithfulness
drops below 0.85.

## The one-paragraph pitch

*"I built a production-shaped, multimodal, agentic RAG platform over engineering
docs, code, diagrams, and incidents. It routes across a tiered Claude stack, uses
two-stage hybrid retrieval with reranking over pgvector + Voyage embeddings,
grounds every answer in cited sources, enforces row-level access control, and is
measured with RAGAS and traced with LangSmith — with a CI quality gate and a
per-query cost model, deployed via Docker/GitHub Actions."*
