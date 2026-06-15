from __future__ import annotations
import logging
from typing import Optional

import instructor
import openai

from app.schemas.financial import IncomeStatementMetrics, INCOME_STATEMENT_SCHEMA_VERSION
from app.extraction.validators import cross_validate_income_statement
from app.db.financials import store_income_statement

try:
    from app.llm.cost import compute_cost_usd
except ImportError:
    def compute_cost_usd(provider, model, input_tokens, output_tokens):
        return None

logger = logging.getLogger(__name__)

EXTRACTION_SYSTEM_PROMPT = """
You are a financial data extraction specialist working with SEC filings.

Rules:
1. Extract ONLY values explicitly stated in the provided text.
   Do NOT use prior knowledge of the company. Text only.
2. If a value is not present in the text, return null for Optional fields.
   Never fabricate a plausible number.
3. reporting_unit: preserve whatever unit the filing uses (millions/thousands/billions).
   Do not convert numbers.
4. Parentheses around numbers mean negative: (1,234) = -1234.
5. extraction_confidence:
   - 'high'   = all values directly stated
   - 'medium' = some values computed from stated numbers
   - 'low'    = significant inference or ambiguity
"""


def build_extraction_prompt(
    ticker: str,
    fiscal_year: int,
    period_type: str,
    section_text: str,
    fiscal_quarter: Optional[str] = None,
) -> str:
    period_str = f"{fiscal_year} {fiscal_quarter}" if fiscal_quarter else str(fiscal_year)
    return (
        f"Extract income statement metrics for {ticker}, period: {period_str} ({period_type}).\n\n"
        f"Filing text:\n\n{section_text}\n\n"
        f"Focus ONLY on the {period_str} period. "
        f"If multiple periods are present, extract only {period_str}."
    )


async def extract_income_statement(
    ticker: str,
    fiscal_year: int,
    period_type: str,
    section_text: str,
    fiscal_quarter: Optional[str] = None,
    model: str = "gpt-4o",
    db=None,
) -> tuple[IncomeStatementMetrics, dict]:

    # 1. Build prompt
    prompt = build_extraction_prompt(
        ticker, fiscal_year, period_type, section_text, fiscal_quarter
    )

    # 2. Instructor + OpenAI
    raw_client = openai.AsyncOpenAI()
    client = instructor.from_openai(raw_client)

    metrics, completion = await client.chat.completions.create_with_completion(
        model=model,
        messages=[
            {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
            {"role": "user",   "content": prompt},
        ],
        response_model=IncomeStatementMetrics,
        max_retries=3,
        temperature=0,
        max_tokens=1024,
    )

    input_tokens  = completion.usage.prompt_tokens
    output_tokens = completion.usage.completion_tokens
    model_used    = completion.model
    finish_reason = completion.choices[0].finish_reason

    # 3. Cross-validate
    warnings = cross_validate_income_statement(metrics)
    if warnings:
        if metrics.extraction_confidence == "high":
            metrics.extraction_confidence = "medium"
        for w in warnings:
            logger.warning("Cross-validation [%s %d]: %s", ticker, fiscal_year, w)

    # 4. Cost tracking
    cost_usd = compute_cost_usd("openai", model_used, input_tokens, output_tokens)

    if db is not None:
        try:
            await db.execute(
                """
                INSERT INTO llm_calls
                    (provider, model, purpose, input_tokens, output_tokens,
                     cost_usd, success, finish_reason, schema_version)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                """,
                "openai", model_used, "extraction",
                input_tokens, output_tokens, cost_usd,
                True, finish_reason, INCOME_STATEMENT_SCHEMA_VERSION,
            )
        except Exception as e:
            logger.error("Cost ledger write failed: %s", e)

    # 5. Store
    metadata = {
        "model":               model_used,
        "input_tokens":        input_tokens,
        "output_tokens":       output_tokens,
        "cost_usd":            cost_usd,
        "validation_warnings": warnings,
        "schema_version":      INCOME_STATEMENT_SCHEMA_VERSION,
        "finish_reason":       finish_reason,
    }

    if db is not None:
        await store_income_statement(db, metrics, metadata)

    return metrics, metadata
