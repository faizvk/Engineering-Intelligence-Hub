-- Operational tables: per-request cost ledger and user feedback.
-- (chat_history for multi-turn is created by langchain_postgres'
--  PostgresChatMessageHistory.create_tables(); not hand-rolled here.)
--
-- Runs on first boot via docker-entrypoint-initdb.d. For an existing volume,
-- apply this file as a migration: `make db-shell < infra/db/003_ops.sql`.

CREATE TABLE IF NOT EXISTS request_costs (
    id                          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    conversation_id             TEXT,
    model                       TEXT          NOT NULL,
    input_tokens                INT           NOT NULL DEFAULT 0,
    output_tokens               INT           NOT NULL DEFAULT 0,
    cache_read_input_tokens     INT           NOT NULL DEFAULT 0,
    cache_creation_input_tokens INT           NOT NULL DEFAULT 0,
    cost_usd                    NUMERIC(12, 6) NOT NULL DEFAULT 0,
    created_at                  TIMESTAMPTZ   NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS request_costs_created_idx ON request_costs (created_at);

CREATE TABLE IF NOT EXISTS feedback (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    answer_id   TEXT,
    run_id      TEXT,                       -- LangSmith run id, to attach feedback to a trace
    rating      INT          NOT NULL,      -- +1 / -1
    reason      TEXT,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT now()
);
