"""baseline: canonical chunk tables, indexes, and ops tables

Idempotent (IF NOT EXISTS) so it is safe to run after the docker init-SQL has
already created the schema, and authoritative for managed Postgres where init
scripts can't be mounted.

Revision ID: 0001_baseline
Revises:
Create Date: 2026-06-26
"""

from alembic import op

revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None

_CHUNK_TABLE = """
CREATE TABLE IF NOT EXISTS {name} (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    content         TEXT         NOT NULL,
    embedding       vector(1024) NOT NULL,
    doc_type        TEXT         NOT NULL,
    source_uri      TEXT         NOT NULL,
    chunk_index     INT          NOT NULL DEFAULT 0,
    repo            TEXT,
    language        TEXT,
    title           TEXT,
    content_sha256  TEXT         NOT NULL,
    acl             TEXT[]       NOT NULL DEFAULT '{{}}',
    metadata        JSONB        NOT NULL DEFAULT '{{}}',
    content_tsv     tsvector GENERATED ALWAYS AS (to_tsvector('english', content)) STORED,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    UNIQUE (source_uri, chunk_index)
)
"""

_STATEMENTS = [
    "CREATE EXTENSION IF NOT EXISTS vector",
    _CHUNK_TABLE.format(name="prose_chunks"),
    _CHUNK_TABLE.format(name="code_chunks"),
    "CREATE INDEX IF NOT EXISTS prose_embedding_hnsw ON prose_chunks USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64)",
    "CREATE INDEX IF NOT EXISTS code_embedding_hnsw ON code_chunks USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64)",
    "CREATE INDEX IF NOT EXISTS prose_tsv_gin ON prose_chunks USING gin (content_tsv)",
    "CREATE INDEX IF NOT EXISTS code_tsv_gin ON code_chunks USING gin (content_tsv)",
    "CREATE INDEX IF NOT EXISTS prose_acl_gin ON prose_chunks USING gin (acl)",
    "CREATE INDEX IF NOT EXISTS code_acl_gin ON code_chunks USING gin (acl)",
    "CREATE INDEX IF NOT EXISTS prose_meta_gin ON prose_chunks USING gin (metadata)",
    "CREATE INDEX IF NOT EXISTS code_meta_gin ON code_chunks USING gin (metadata)",
    "CREATE INDEX IF NOT EXISTS prose_created_idx ON prose_chunks (created_at)",
    """CREATE TABLE IF NOT EXISTS embed_cache (
        content_sha256 TEXT NOT NULL, model TEXT NOT NULL,
        embedding vector(1024) NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        PRIMARY KEY (content_sha256, model))""",
    """CREATE TABLE IF NOT EXISTS request_costs (
        id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY, conversation_id TEXT, user_id TEXT,
        model TEXT NOT NULL, input_tokens INT NOT NULL DEFAULT 0, output_tokens INT NOT NULL DEFAULT 0,
        cache_read_input_tokens INT NOT NULL DEFAULT 0, cache_creation_input_tokens INT NOT NULL DEFAULT 0,
        cost_usd NUMERIC(12,6) NOT NULL DEFAULT 0, created_at TIMESTAMPTZ NOT NULL DEFAULT now())""",
    """CREATE TABLE IF NOT EXISTS feedback (
        id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY, answer_id TEXT, run_id TEXT,
        rating INT NOT NULL, reason TEXT, created_at TIMESTAMPTZ NOT NULL DEFAULT now())""",
    """CREATE TABLE IF NOT EXISTS ingest_jobs (
        id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY, source_uri TEXT NOT NULL,
        doc_type TEXT NOT NULL, content TEXT NOT NULL, acl TEXT[] NOT NULL DEFAULT '{all}',
        status TEXT NOT NULL DEFAULT 'queued', error TEXT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(), processed_at TIMESTAMPTZ)""",
]


def upgrade() -> None:
    for stmt in _STATEMENTS:
        op.execute(stmt)


def downgrade() -> None:
    for table in ("ingest_jobs", "feedback", "request_costs", "embed_cache", "code_chunks", "prose_chunks"):
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
