## What & why

<!-- One or two sentences. Link the issue if there is one. -->

## Changes

-

## Checklist

- [ ] `make test` is green (unit tests don't need external services)
- [ ] `make lint` passes
- [ ] Added/updated a test for the behavior change
- [ ] Respected the layering (core ⟵ backend/ingestion/evals; no cross-imports)
- [ ] No secrets, no `temperature`/`budget_tokens` on Claude 4.x
- [ ] If retrieval/prompt/chunking changed: noted the expected eval impact
