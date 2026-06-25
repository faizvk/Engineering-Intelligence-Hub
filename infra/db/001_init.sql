-- Runs once, on an empty data directory, via docker-entrypoint-initdb.d.
-- Enables pgvector and sanity-checks the install (visible in `docker compose logs db`).

CREATE EXTENSION IF NOT EXISTS vector;

DO $$
BEGIN
  RAISE NOTICE 'pgvector version: %',
    (SELECT extversion FROM pg_extension WHERE extname = 'vector');
END $$;
