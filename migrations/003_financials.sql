CREATE TABLE IF NOT EXISTS income_statements (
    id                    UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at            TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at            TIMESTAMPTZ  NOT NULL DEFAULT NOW(),

    ticker                VARCHAR(10)  NOT NULL,
    company_name          VARCHAR(255),
    fiscal_year           SMALLINT     NOT NULL,
    fiscal_quarter        VARCHAR(2),
    period_type           VARCHAR(20)  NOT NULL,
    filing_accession      VARCHAR(50),

    currency              VARCHAR(3)   NOT NULL DEFAULT 'USD',
    reporting_unit        VARCHAR(20)  NOT NULL DEFAULT 'millions',
    revenue               NUMERIC(16, 4),
    gross_profit          NUMERIC(16, 4),
    operating_income      NUMERIC(16, 4),
    net_income            NUMERIC(16, 4),
    ebitda                NUMERIC(16, 4),
    eps_basic             NUMERIC(12, 4),
    eps_diluted           NUMERIC(12, 4),
    gross_margin_pct      NUMERIC(8, 4),
    operating_margin_pct  NUMERIC(8, 4),
    net_margin_pct        NUMERIC(8, 4),

    extraction_confidence VARCHAR(10)  NOT NULL,
    schema_version        VARCHAR(20),
    validation_warnings   JSONB,
    notes                 TEXT,

    CONSTRAINT uq_income_statement
        UNIQUE (ticker, fiscal_year, fiscal_quarter, period_type)
);

CREATE TABLE IF NOT EXISTS segment_revenues (
    id                   UUID  PRIMARY KEY DEFAULT gen_random_uuid(),
    income_statement_id  UUID  NOT NULL REFERENCES income_statements(id) ON DELETE CASCADE,
    segment_name         VARCHAR(255) NOT NULL,
    revenue              NUMERIC(16, 4),
    yoy_growth_pct       NUMERIC(8, 4)
);

CREATE INDEX IF NOT EXISTS idx_income_stmts_ticker
    ON income_statements (ticker);

CREATE INDEX IF NOT EXISTS idx_income_stmts_ticker_year
    ON income_statements (ticker, fiscal_year DESC);

CREATE INDEX IF NOT EXISTS idx_income_stmts_confidence
    ON income_statements (extraction_confidence)
    WHERE extraction_confidence IN ('medium', 'low');
