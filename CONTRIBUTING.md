# Contributing

## Setup

```bash
cp .env.example .env          # fill ANTHROPIC_API_KEY and VOYAGE_API_KEY
make up                       # Postgres + pgvector
uv sync --all-extras          # or: pip install -e ".[dev,eval]"
make hooks                    # install pre-commit
```

## Workflow

- `make test` — pytest (unit tests run with no external services; integration
  tests skip gracefully without a DB/keys).
- `make lint` / `make fmt` — ruff + mypy.
- `make eval` — retrieval metrics + RAGAS quality gate (needs keys + a corpus).
- Keep the suite green; add a test with each behavior change. Pure-Python logic
  (fusion, scoring, ACL, redaction, metrics) should stay importable without the
  heavy stack so it tests cheaply.

## Conventions

- Conventional-commit style subjects (`feat(rag): …`, `fix: …`, `docs: …`).
- Respect the layering: `core/` imports nothing from `backend/ingestion/evals`;
  `backend/` imports `core/` only; the `/ingest` endpoint enqueues via `core.db`
  and never imports the ingestion pipeline.
- Anthropic-specific knobs (adaptive thinking, cache breakpoints, citations) are
  passed through explicitly — don't let the abstraction hide them. No
  `temperature`/`top_p`/`top_k` on Claude 4.x.
- Secrets never enter source, a committed file, or an image layer.

See [`ARCHITECTURE.md`](ARCHITECTURE.md) and [`SECURITY.md`](SECURITY.md).
