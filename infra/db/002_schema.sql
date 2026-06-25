-- The single canonical schema the whole system targets.
--
-- Two tables because the prose embedder (voyage-3.5) and the code embedder
-- (voyage-code-3) live in different vector spaces and can have different
-- dimensions; mixing them in one column is not meaningful. Both tables share
-- the same shape so the retrieval layer queries them uniformly.
--
-- EMBED_DIM (1024) MUST equal core.settings.embed_dim and the Voyage output
-- dimension, or inserts fail.

CREATE TABLE IF NOT EXISTS prose_chunks (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    content         TEXT         NOT NULL,
    embedding       vector(1024) NOT NULL,
    doc_type        TEXT         NOT NULL,                 -- 'doc' | 'incident' | 'diagram'
    source_uri      TEXT         NOT NULL,
    chunk_index     INT          NOT NULL DEFAULT 0,
    repo            TEXT,
    language        TEXT,
    title           TEXT,
    content_sha256  TEXT         NOT NULL,                 -- incremental re-index + embed cache
    acl             TEXT[]       NOT NULL DEFAULT '{}',    -- groups allowed to see this chunk
    metadata        JSONB        NOT NULL DEFAULT '{}',
    content_tsv     tsvector GENERATED ALWAYS AS (to_tsvector('english', content)) STORED,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    UNIQUE (source_uri, chunk_index)                       -- idempotent upsert key
);

-- Code: source files (voyage-code-3). Same shape, separate vector space.
CREATE TABLE IF NOT EXISTS code_chunks (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    content         TEXT         NOT NULL,
    embedding       vector(1024) NOT NULL,
    doc_type        TEXT         NOT NULL,                 -- 'code'
    source_uri      TEXT         NOT NULL,
    chunk_index     INT          NOT NULL DEFAULT 0,
    repo            TEXT,
    language        TEXT,
    title           TEXT,
    content_sha256  TEXT         NOT NULL,
    acl             TEXT[]       NOT NULL DEFAULT '{}',
    metadata        JSONB        NOT NULL DEFAULT '{}',
    content_tsv     tsvector GENERATED ALWAYS AS (to_tsvector('english', content)) STORED,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    UNIQUE (source_uri, chunk_index)
);

-- ---- Indexes (mirrored across both tables) ----
-- HNSW + cosine: matches the L2-normalized Voyage vectors and the <=> query operator.
-- Building the index on an empty table is supported (HNSW), so we can ingest incrementally.
CREATE INDEX IF NOT EXISTS prose_embedding_hnsw ON prose_chunks
    USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);
CREATE INDEX IF NOT EXISTS code_embedding_hnsw ON code_chunks
    USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);

-- BM25-adjacent lexical search.
CREATE INDEX IF NOT EXISTS prose_tsv_gin ON prose_chunks USING gin (content_tsv);
CREATE INDEX IF NOT EXISTS code_tsv_gin  ON code_chunks  USING gin (content_tsv);

-- Row-level access control (chunk visible if acl && user's groups).
CREATE INDEX IF NOT EXISTS prose_acl_gin ON prose_chunks USING gin (acl);
CREATE INDEX IF NOT EXISTS code_acl_gin  ON code_chunks  USING gin (acl);

-- Metadata pre-filtering (repo / service / severity live in metadata jsonb).
CREATE INDEX IF NOT EXISTS prose_meta_gin ON prose_chunks USING gin (metadata);
CREATE INDEX IF NOT EXISTS code_meta_gin  ON code_chunks  USING gin (metadata);

-- Relevance/recency filters and dedup lookups.
CREATE INDEX IF NOT EXISTS prose_doctype_idx ON prose_chunks (doc_type);
CREATE INDEX IF NOT EXISTS prose_created_idx ON prose_chunks (created_at);
CREATE INDEX IF NOT EXISTS prose_sha_idx     ON prose_chunks (content_sha256);
CREATE INDEX IF NOT EXISTS code_sha_idx      ON code_chunks  (content_sha256);
