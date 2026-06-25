# Deploy

The sweet spot for a portfolio: **Fly.io or Render** for the API + **Vercel** for
the frontend + **managed Postgres with pgvector**. Real, cheap, reviewable.

## Backend (Fly.io)

```bash
fly launch --no-deploy            # uses fly.toml + infra/backend.Dockerfile
fly secrets set ANTHROPIC_API_KEY=... VOYAGE_API_KEY=... \
                DATABASE_URL=postgresql+psycopg://... JWT_PUBLIC_KEY=...
fly deploy
```

Attach Fly Postgres (or any managed PG), then run migrations once:
`alembic upgrade head` (enables `vector` + creates the schema, idempotent).

## Backend (Render)

`render.yaml` provisions the web service + a managed Postgres in one blueprint.
Set `ANTHROPIC_API_KEY` / `VOYAGE_API_KEY` / `CORS_ALLOW_ORIGINS` in the
dashboard (they're `sync: false`). Run `alembic upgrade head` as a one-off job.

## Frontend (Vercel)

Deploy `frontend/` (zero-config Next.js). Set `NEXT_PUBLIC_API_URL` to the API's
public URL. Point the API's `CORS_ALLOW_ORIGINS` at the Vercel origin.

## Managed Postgres + pgvector

AWS RDS/Aurora, Render, Railway, Supabase, and Neon all ship the `vector`
extension. Connect, `CREATE EXTENSION IF NOT EXISTS vector;` (the baseline
migration does this), and the schema + HNSW indexes work unchanged. Pin index
build params and extension version so dev and prod match.

## Secrets

No key in source, in a committed file, or in an image layer. Local: gitignored
`.env`. CI: GitHub Actions secrets. Cloud: the platform's secret store, mounted
as env at runtime. Rotate at the provider if one leaks.
