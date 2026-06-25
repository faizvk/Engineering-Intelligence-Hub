-- Ingestion job queue. The API enqueues (it must not import the ingestion
-- pipeline); the ingestion worker (python -m ingestion.jobs) processes queued
-- rows out of band — keeping the online and offline paths decoupled.

CREATE TABLE IF NOT EXISTS ingest_jobs (
    id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_uri   TEXT         NOT NULL,
    doc_type     TEXT         NOT NULL,          -- 'doc' | 'code' | 'incident' | 'diagram'
    content      TEXT         NOT NULL,
    acl          TEXT[]       NOT NULL DEFAULT '{all}',
    status       TEXT         NOT NULL DEFAULT 'queued',  -- queued|processing|done|error
    error        TEXT,
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT now(),
    processed_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS ingest_jobs_status_idx ON ingest_jobs (status);
