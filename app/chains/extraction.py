import json
import logging

import instructor
import openai
from langchain_core.runnables import RunnableLambda

from app.prompts.registry import load_prompt
from app.schemas.financial import IncomeStatementMetrics, INCOME_STATEMENT_SCHEMA_VERSION
from app.extraction.validators import cross_validate_income_statement, apply_validation_warnings
from app.llm.cost import compute_cost_usd
from app.llm.cache import get_cached_response, set_cached_response
from app.llm.budget import ContextBudget
from app.config import CACHE_TTL_SECONDS

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT_VERSION = "v1"
EXTRACTION_MODEL = "gpt-4o"


def build_extraction_chain(
    model: str = EXTRACTION_MODEL,
    prompt_version: str = EXTRACTION_PROMPT_VERSION,
):
    """
    Build the income statement extraction chain.

    Input dict: {ticker, fiscal_year, period_type, section_text, period_str,
                 fiscal_quarter (optional), db (optional)}
    Output: IncomeStatementMetrics
    """
    spec = load_prompt("extraction", prompt_version)

    async def _extract(inputs: dict) -> IncomeStatementMetrics:
        ticker = inputs["ticker"]
        period_str = inputs.get("period_str", str(inputs.get("fiscal_year", "unknown")))
        period_type = inputs.get("period_type", "annual")
        section_text = inputs["section_text"]

        system_msg = spec.system

        # Apply context budget to fit large filings
        budget = ContextBudget(model)
        budgeted_text = await budget.budget_section_text(
            section_text,
            system_msg,
            spec.user,
            ticker=ticker,
            period_str=period_str,
            period_type=period_type,
        )

        user_msg = spec.user.format(
            ticker=ticker,
            period_str=period_str,
            period_type=period_type,
            section_text=budgeted_text,
        )

        cached = await get_cached_response(model, prompt_version, user_msg)
        if cached:
            logger.info(f"Cache hit for {ticker} {period_str}")
            metrics = IncomeStatementMetrics(**cached["metrics"])
            metrics.ticker = ticker
            metrics.fiscal_year = inputs.get("fiscal_year", 0)
            metrics.fiscal_quarter = inputs.get("fiscal_quarter")
            metrics.period_type = period_type
            return metrics

        raw_client = openai.AsyncOpenAI()
        client = instructor.from_openai(raw_client)

        metrics, completion = await client.chat.completions.create_with_completion(
            model=model,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user",   "content": user_msg},
            ],
            response_model=IncomeStatementMetrics,
            max_retries=3,
            temperature=0,
            max_tokens=1024,
        )

        # Inject identity fields
        metrics.ticker = ticker
        metrics.fiscal_year = inputs.get("fiscal_year", 0)
        metrics.fiscal_quarter = inputs.get("fiscal_quarter")
        metrics.period_type = period_type
        metrics.schema_version = INCOME_STATEMENT_SCHEMA_VERSION

        # Cross-validate
        warnings = cross_validate_income_statement(metrics)
        if warnings:
            metrics = apply_validation_warnings(metrics, warnings)

        # Cache the result (store serializable dict)
        cache_payload = {
            "metrics": json.loads(metrics.model_dump_json()),
            "warnings": warnings,
        }
        await set_cached_response(model, prompt_version, user_msg, cache_payload, CACHE_TTL_SECONDS)

        # Log cost if db provided
        if db := inputs.get("db"):
            input_tokens = completion.usage.prompt_tokens
            output_tokens = completion.usage.completion_tokens
            cost_usd = compute_cost_usd("openai", completion.model, input_tokens, output_tokens)
            try:
                await db.execute(
                    """
                    INSERT INTO llm_calls
                      (provider, model, purpose, input_tokens, output_tokens,
                       cost_usd, latency_ms, success, finish_reason, prompt_version)
                    VALUES ('openai', $1, 'extraction', $2, $3, $4, 0, true, $5, $6)
                    """,
                    completion.model, input_tokens, output_tokens,
                    cost_usd, completion.choices[0].finish_reason, prompt_version,
                )
            except Exception as e:
                logger.error("Cost ledger write failed: %s", e)

        return metrics

    return RunnableLambda(_extract)
