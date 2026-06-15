from __future__ import annotations
import json
import logging
from app.schemas.financial import IncomeStatementMetrics

logger = logging.getLogger(__name__)


async def store_income_statement(
    db,
    metrics: IncomeStatementMetrics,
    metadata: dict,
) -> None:
    """
    Upsert income statement into postgres.
    ON CONFLICT: overwrites the existing row (re-extraction updates data).
    """
    await db.execute(
        """
        INSERT INTO income_statements (
            ticker, company_name, fiscal_year, fiscal_quarter, period_type,
            currency, reporting_unit,
            revenue, gross_profit, operating_income, net_income, ebitda,
            eps_basic, eps_diluted,
            gross_margin_pct, operating_margin_pct, net_margin_pct,
            extraction_confidence, schema_version, validation_warnings, notes,
            updated_at
        )
        VALUES (
            $1, $2, $3, $4, $5,
            $6, $7,
            $8, $9, $10, $11, $12,
            $13, $14,
            $15, $16, $17,
            $18, $19, $20, $21,
            NOW()
        )
        ON CONFLICT (ticker, fiscal_year, fiscal_quarter, period_type) DO UPDATE SET
            company_name          = EXCLUDED.company_name,
            revenue               = EXCLUDED.revenue,
            gross_profit          = EXCLUDED.gross_profit,
            operating_income      = EXCLUDED.operating_income,
            net_income            = EXCLUDED.net_income,
            ebitda                = EXCLUDED.ebitda,
            eps_basic             = EXCLUDED.eps_basic,
            eps_diluted           = EXCLUDED.eps_diluted,
            gross_margin_pct      = EXCLUDED.gross_margin_pct,
            operating_margin_pct  = EXCLUDED.operating_margin_pct,
            net_margin_pct        = EXCLUDED.net_margin_pct,
            extraction_confidence = EXCLUDED.extraction_confidence,
            schema_version        = EXCLUDED.schema_version,
            validation_warnings   = EXCLUDED.validation_warnings,
            notes                 = EXCLUDED.notes,
            updated_at            = NOW()
        """,
        metrics.ticker,
        metrics.company_name,
        metrics.fiscal_year,
        metrics.fiscal_quarter,
        metrics.period_type,
        "USD",
        metrics.reporting_unit,
        metrics.revenue,
        metrics.gross_profit,
        metrics.operating_income,
        metrics.net_income,
        metrics.ebitda,
        metrics.eps_basic,
        metrics.eps_diluted,
        metrics.gross_margin_pct,
        metrics.operating_margin_pct,
        metrics.net_margin_pct,
        metrics.extraction_confidence,
        metadata.get("schema_version"),
        json.dumps(metadata.get("validation_warnings", [])),
        metrics.notes,
    )
    logger.info(
        "Stored income statement: %s FY%d (%s) confidence=%s",
        metrics.ticker,
        metrics.fiscal_year,
        metrics.period_type,
        metrics.extraction_confidence,
    )
