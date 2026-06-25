-- Cross-source embedding cache: never re-embed identical content, keyed by
-- (content_sha256, model). Survives chunk deletion/re-add and reuses vectors
-- when the same text appears in multiple sources.
--
-- Runs on first boot; apply to an existing volume with:
--   make db-shell < infra/db/004_embed_cache.sql

CREATE TABLE IF NOT EXISTS embed_cache (
    content_sha256  TEXT         NOT NULL,
    model           TEXT         NOT NULL,   -- the Voyage model that produced it
    embedding       vector(1024) NOT NULL,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    PRIMARY KEY (content_sha256, model)
);
