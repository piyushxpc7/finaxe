CREATE TABLE llm_calls (
    id UUID PRIMARY KEY,
    ts TIMESTAMPTZ NOT NULL,
    provider TEXT,
    model TEXT,
    purpose TEXT,
    input_tokens INTEGER,
    output_tokens INTEGER,
    cost_usd NUMERIC,
    latency_ms INTEGER,
    finish_reason TEXT,
    success BOOLEAN
);

CREATE INDEX idx_llm_calls_ts ON llm_calls(ts);
CREATE INDEX idx_llm_calls_provider ON llm_calls(provider);
CREATE INDEX idx_llm_calls_model ON llm_calls(model);
